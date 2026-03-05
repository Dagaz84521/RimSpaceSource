from flask import Flask, request, jsonify
import os
import json
import argparse
import character_state_translator
import environment_translator
import recipe_provider
import configs
import llm
from react_tools import dispatch_tool_action, get_react_tools_description

app = Flask(__name__)

REACT_MAX_STEPS = int(os.getenv('REACT_MAX_STEPS', '8'))
LOG_LLM_THOUGHTS = os.getenv('LOG_LLM_THOUGHTS', '1') == '1'
PRINT_PROMPTS = False


def _truncate_for_log(text, max_len=500):
    if text is None:
        return ""
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "...<truncated>"


def _log_react_step(character_name, game_round, llm_turn, action_count, raw_output, parsed):
    if not LOG_LLM_THOUGHTS:
        return
    if isinstance(parsed, dict):
        thought = parsed.get("Thought") or parsed.get("thought") or ""
        msg_type = parsed.get("type", "")
        tool = parsed.get("tool", "")
        command = parsed.get("command", "")
        evidence = parsed.get("evidence", "")
        app.logger.info(
            "[ReAct][%s][game_round=%s][llm_turn=%s][tool_calls=%s] type=%s tool=%s command=%s thought=%s evidence=%s",
            character_name,
            game_round,
            llm_turn,
            action_count,
            msg_type,
            tool,
            command,
            _truncate_for_log(thought, 300),
            _truncate_for_log(evidence, 300)
        )
        app.logger.info(
            "[ReAct][%s][game_round=%s][llm_turn=%s] raw=%s",
            character_name,
            game_round,
            llm_turn,
            _truncate_for_log(raw_output, 800)
        )
    else:
        app.logger.info(
            "[ReAct][%s][game_round=%s][llm_turn=%s] raw(non-json)=%s",
            character_name,
            game_round,
            llm_turn,
            _truncate_for_log(raw_output, 800)
        )


def _log_mindagent_output(character_name, raw_output, parsed):
    if not LOG_LLM_THOUGHTS:
        return
    thought = ""
    command = ""
    if isinstance(parsed, dict):
        thought = parsed.get("Thought") or parsed.get("thought") or ""
        command = parsed.get("command", "")
    app.logger.info(
        "[MindAgent][%s] command=%s thought=%s raw=%s",
        character_name,
        command,
        _truncate_for_log(thought, 300),
        _truncate_for_log(raw_output, 800)
    )


def _get_character_by_name(data, character_name):
    characters_data = data.get("Characters", {}).get("Characters", [])
    for character in characters_data:
        if character.get("CharacterName") == character_name:
            return character
    return None


def _get_character_location(data, character_name):
    character = _get_character_by_name(data, character_name)
    if not character:
        return ""
    return character.get("CurrentLocation", "")


def _select_profile_for_character(data, character_name):
    character = _get_character_by_name(data, character_name)
    if character:
        skills = set(character.get("CharacterSkills", []) or [])
        if "CanFarm" in skills:
            return configs.PROFILE_FARMER
        if "CanCraft" in skills:
            return configs.PROFILE_CRAFTER
        if "CanCook" in skills:
            return getattr(configs, "PROFILE_CHEF", configs.PROFILE_CRAFTER)

    lowered_name = str(character_name).lower()
    if "farmer" in lowered_name:
        return configs.PROFILE_FARMER
    if "chef" in lowered_name:
        return getattr(configs, "PROFILE_CHEF", configs.PROFILE_CRAFTER)
    if "crafter" in lowered_name:
        return configs.PROFILE_CRAFTER

    return configs.PROFILE_CRAFTER


def _extract_json_object(text):
    """尽量从模型输出中提取 JSON 对象。"""
    if text is None:
        return None
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
            candidate = "\n".join(lines[1:-1]).strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
    try:
        return json.loads(candidate)
    except Exception:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        segment = candidate[start:end + 1]
        try:
            return json.loads(segment)
        except Exception:
            return None
    return None


def _actor_type_contains(actor_type, name):
    return name.lower() in str(actor_type or "").lower()


def _build_current_task_text(data):
    """从环境中提取当前任务描述（仅文本，不做分解/Goal）。"""
    environment = data.get("Environment", {}) or {}
    actors = environment.get("Actors", [])
    if isinstance(actors, dict):
        actors = list(actors.values())

    task_lines = []

    for actor in actors:
        actor_name = actor.get("ActorName", "")
        actor_type = actor.get("ActorType", "")

        if _actor_type_contains(actor_type, "CultivateChamber"):
            cultivate_info = actor.get("CultivateInfo", {}) or {}
            phase = str(cultivate_info.get("CurrentPhase", ""))
            if "WaitingToPlant" in phase:
                target_type = str(cultivate_info.get("TargetCultivateType", "")).replace("ECultivateType::ECT_", "")
                target_text = target_type if target_type else "作物"
                task_lines.append(f"- 在 {actor_name} 种植 {target_text}")
            elif "ReadyToHarvest" in phase:
                current_type = str(cultivate_info.get("CurrentCultivateType", "")).replace("ECultivateType::ECT_", "")
                current_text = current_type if current_type else "作物"
                task_lines.append(f"- 在 {actor_name} 收获 {current_text}")

        if _actor_type_contains(actor_type, "WorkStation") or _actor_type_contains(actor_type, "Stove"):
            task_list = actor.get("TaskList", {}) or {}
            if not isinstance(task_list, dict):
                continue
            for task_id, count in task_list.items():
                try:
                    task_count = int(count)
                except Exception:
                    task_count = 0
                if task_count <= 0:
                    continue

                recipe = recipe_provider.get_recipe_by_ID(task_id)
                if recipe:
                    task_name = recipe.get("TaskName") or f"任务ID={task_id}"
                    product_id = recipe.get("ProductID", "")
                    if product_id != "":
                        task_lines.append(f"- {actor_name} 需要 {task_name} x{task_count} (ProductID={product_id})")
                    else:
                        task_lines.append(f"- {actor_name} 需要 {task_name} x{task_count}")
                else:
                    task_lines.append(f"- {actor_name} 需要执行任务 TaskID={task_id} x{task_count}")

    if not task_lines:
        return "当前暂无明确生产任务，可先观察环境或执行支援/等待。"

    return "\n".join(task_lines)


def _build_react_system_prompt(data, character_name):
    selected_profile = _select_profile_for_character(data, character_name)
    return configs.SYSTEM_PROMPT_REACT.format(
        specific_profile=selected_profile,
        react_tools=get_react_tools_description(),
        react_max_steps=REACT_MAX_STEPS,
    ).strip()


def _build_react_user_prompt(data, character_name):
    round_number = data.get("RoundNumber", "")
    previous_belief = data.get("PreviousBelief", "")
    execution_feedback = data.get("ExecutionFeedback", "")
    return configs.USER_PROMPT_REACT_TEMPLATE.format(
        character_name=character_name,
        round_number=round_number,
        previous_belief=previous_belief,
        execution_feedback=execution_feedback,
        react_max_steps=REACT_MAX_STEPS,
        current_task=_build_current_task_text(data),
    ).strip()


def _print_prompts_if_needed(mode, character_name, system_prompt, user_prompt):
    if not PRINT_PROMPTS:
        return
    print(f"\n[Prompt][{mode}][{character_name}] System Prompt:\n{system_prompt}", flush=True)
    print(f"\n[Prompt][{mode}][{character_name}] User Prompt:\n{user_prompt}\n", flush=True)


@app.before_request
def _trace_prompt_request():
    if not PRINT_PROMPTS:
        return
    if request.path not in ('/GetInstructionMindAgent', '/GetInstructionReAct'):
        return
    payload = request.get_json(silent=True) or {}
    target_agent = payload.get('TargetAgent', '')
    print(f"[PromptTrace] hit={request.path} target={target_agent}", flush=True)


@app.route('/GetInstructionMindAgent', methods=['POST'])
def get_instruction_mindagent():
    """POST endpoint that returns an instruction JSON.

    Accepts optional JSON body with a `task` field to customize the instruction.
    """
    data = request.get_json(silent=True) or {}

    character_name = data.get("TargetAgent", "")
        
    # 解析请求
    if not character_name:
        return jsonify({
            "status": "error",
            "message": "Missing TargetAgent"
        }), 400
    
    # 获取游戏状态信息
    system_prompt, user_prompt = generate_prompts_mindagent(data, character_name)
    _print_prompts_if_needed("MindAgent", character_name, system_prompt, user_prompt)
    call_model_response, tokens_used = llm.call_model(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model=configs.LLM_MODEL,
        temperature=0.2,
        max_tokens=4096
    )
    # 解析LLM响应
    try:
        response_json = call_model_response.strip()
        if response_json.startswith("```") and response_json.endswith("```"):
            response_json = response_json[3:-3].strip()
        instruction_data = eval(response_json)  # 注意：使用eval存在安全风险，确保LLM输出可信
        _log_mindagent_output(character_name, call_model_response, instruction_data)
        command = instruction_data.get("command", "Wait")
        aux_param = instruction_data.get("aux_param", "")
        belief = instruction_data.get("Belief", "")
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to parse LLM response: {e}"
        }), 500
    resp = {
        "status": "success",
        "instruction": {
            "CommandType": command,
            "aux_param": aux_param,
            "Belief": belief
        }
    }
    
    return jsonify(resp), 200

def generate_prompts_mindagent(data, character_name):
    characters_data = data.get("Characters", {}).get("Characters", [])
    environment = data.get("Environment", {})
    round_number = data.get("RoundNumber", "")
    previous_belief = data.get("PreviousBelief", "")
    execution_feedback = data.get("ExecutionFeedback", "")
    recipe_text = recipe_provider.get_all_recipes_prompt()
    world_state = environment_translator.get_all_actor_names_prompt(environment)
    world_state = world_state + environment_translator.get_environment_state_prompt(environment)
    if round_number != "":
        world_state = f"当前回合: {round_number}\n" + world_state
    character_state = character_state_translator.get_character_state_prompt(character_name, characters_data)
    selected_profile = _select_profile_for_character(data, character_name)
    system_prompt = configs.SYSTEM_PROMPT_MINDAGENT.format(
        recipe_text=recipe_text,
        specific_profile=selected_profile,
    )
    user_prompt = configs.USER_PROMPT_TEMPLATE.format(
        character_state=character_state,
        world_state=world_state,
        current_task=_build_current_task_text(data),
        previous_belief=previous_belief,
        execution_feedback=execution_feedback,
    )
    
    return system_prompt,user_prompt

@app.route('/GetInstructionReAct', methods=['POST'])
def get_instruction_react():
    data = request.get_json(silent=True) or {}
    character_name = data.get("TargetAgent", "")
    game_round = data.get("RoundNumber", "")

    if not character_name:
        return jsonify({
            "status": "error",
            "message": "Missing TargetAgent"
        }), 400

    context = {
        "data": data,
        "character_name": character_name,
    }

    system_prompt = _build_react_system_prompt(data, character_name)
    user_prompt = _build_react_user_prompt(data, character_name)
    _print_prompts_if_needed("ReAct", character_name, system_prompt, user_prompt)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    total_tokens = 0
    action_count = 0
    max_rounds = REACT_MAX_STEPS + 4
    for step in range(max_rounds):
        llm_turn = step + 1
        call_model_response, tokens_used = llm.call_model(
            messages=messages,
            model=configs.LLM_MODEL,
            temperature=0.2,
            max_tokens=4096
        )
        total_tokens += tokens_used or 0

        parsed = _extract_json_object(call_model_response)
        _log_react_step(character_name, game_round, llm_turn, action_count, call_model_response, parsed)
        if not parsed:
            messages.append({"role": "assistant", "content": call_model_response})
            messages.append({
                "role": "user",
                "content": "Observation: 你的输出不是合法 JSON。请严格输出 JSON 对象。"
            })
            continue

        msg_type = str(parsed.get("type", "")).lower().strip()
        if msg_type == "final":
            command = parsed.get("command", "Wait")
            aux_param = parsed.get("aux_param", "")
            belief = parsed.get("Belief", "")
            evidence = parsed.get("evidence")

            if action_count < REACT_MAX_STEPS and ("工具" in str(belief)) and ("上限" in str(belief) or "达到" in str(belief)):
                messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
                messages.append({
                    "role": "user",
                    "content": f"Observation: 当前本请求工具调用为 {action_count}/{REACT_MAX_STEPS}，并未达到上限。请基于真实计数重新输出 final。"
                })
                continue

            if str(command) == "Move":
                current_location = _get_character_location(data, character_name)
                if current_location and str(aux_param) == str(current_location):
                    messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
                    messages.append({
                        "role": "user",
                        "content": f"Observation: 你当前已在 {current_location}，Move 到同一地点是无效动作。请基于当前地点重新输出 final。"
                    })
                    continue

            evidence_valid = False
            if isinstance(evidence, list) and len(evidence) > 0:
                evidence_valid = True
            if isinstance(evidence, str) and evidence.strip():
                evidence_valid = True

            if not evidence_valid:
                messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
                messages.append({
                    "role": "user",
                    "content": "Observation: final 缺少 evidence 字段。请重新输出 final，并提供 1~3 条 evidence。"
                })
                continue

            return jsonify({
                "status": "success",
                "mode": "ReAct",
                "game_round": game_round,
                "react_steps": llm_turn,
                "llm_turns": llm_turn,
                "tool_calls": action_count,
                "tool_call_limit": REACT_MAX_STEPS,
                "tokens_used": total_tokens,
                "instruction": {
                    "CommandType": command,
                    "aux_param": aux_param,
                    "Belief": belief,
                }
            }), 200

        if msg_type != "action":
            messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
            messages.append({
                "role": "user",
                "content": "Observation: type 字段只能是 action 或 final。"
            })
            continue

        if action_count >= REACT_MAX_STEPS:
            messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
            messages.append({
                "role": "user",
                "content": "Observation: 工具调用次数已达上限。请不要再调用工具，直接输出 type=final。"
            })
            continue

        dispatch_result = dispatch_tool_action(parsed, context)
        action_count += 1
        messages.append({"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)})
        messages.append({
            "role": "user",
            "content": "Observation: " + json.dumps(dispatch_result, ensure_ascii=False)
        })

    return jsonify({
        "status": "success",
        "mode": "ReAct",
        "game_round": game_round,
        "react_steps": max_rounds,
        "llm_turns": max_rounds,
        "tool_calls": action_count,
        "tool_call_limit": REACT_MAX_STEPS,
        "tokens_used": total_tokens,
        "instruction": {
            "CommandType": "Wait",
            "aux_param": "5",
            "Belief": "达到最大推理轮次，先等待"
        }
    }), 200

if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--prompt', action='store_true', help='每次请求时打印 system/user prompt')
    args, _ = parser.parse_known_args()
    PRINT_PROMPTS = args.prompt

    print(f"[Startup] PRINT_PROMPTS={PRINT_PROMPTS}", flush=True)

    port = int(os.getenv('PORT', '5000'))
    # For development only; in production use a WSGI server (gunicorn/uvicorn)
    app.run(host='0.0.0.0', port=port, debug=True)

