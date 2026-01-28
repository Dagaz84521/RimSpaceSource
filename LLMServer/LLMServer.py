"""
LLM服务器 - 处理游戏世界状态，调用LLM做决策，并通过Planner分解为单步指令
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from typing import Dict, Optional
import os
from datetime import datetime

from TaskBlackboard import TaskBlackboard, TaskPriority
from Planner import Planner

# 检查是否安装了OpenAI或其他LLM库
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[警告] 未安装openai库，LLM功能将被禁用")

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化系统
blackboard = TaskBlackboard()
planner = Planner(blackboard)

# 游戏状态缓存
game_state_cache: Dict = {}

# LLM客户端（如果可用）
llm_client = None
if OPENAI_AVAILABLE:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        llm_client = OpenAI(api_key=api_key)
        print("[LLMServer] OpenAI客户端初始化成功")
    else:
        print("[警告] 未设置OPENAI_API_KEY环境变量")


def call_llm_for_decision(
    character_name: str,
    game_state: Dict,
    blackboard_summary: Dict
) -> Dict:
    """
    调用LLM进行高级决策
    
    Returns:
        {
            "action": "Sleep/Eat/Craft/Plant/Harvest/Transport/CheckBlackboard",
            "params": {...}
        }
    """
    # 如果LLM不可用，使用规则引擎
    if not llm_client:
        return rule_based_decision(character_name, game_state, blackboard_summary)
    
    # 构建Prompt
    prompt = build_decision_prompt(character_name, game_state, blackboard_summary)
    
    try:
        response = llm_client.chat.completions.create(
            model="gpt-4o-mini",  # 或使用 gpt-3.5-turbo
            messages=[
                {
                    "role": "system",
                    "content": "你是一个游戏AI助手，负责控制NPC角色。根据角色状态、世界信息和任务，做出合理的决策。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        print(f"[LLM决策] {character_name}: {result.get('action')} - {result.get('reasoning', '')}")
        return result
        
    except Exception as e:
        print(f"[错误] LLM调用失败: {e}")
        return rule_based_decision(character_name, game_state, blackboard_summary)


def build_decision_prompt(
    character_name: str,
    game_state: Dict,
    blackboard_summary: Dict
) -> str:
    """构建LLM决策的Prompt"""
    
    # 获取角色信息
    character_info = game_state.get("Characters", {}).get(character_name, {})
    hunger = character_info.get("Hunger", 100)
    energy = character_info.get("Energy", 100)
    position = character_info.get("Position", "未知")
    inventory = character_info.get("Inventory", [])
    
    # 获取环境信息
    environment = game_state.get("Environment", {})
    
    # 获取黑板任务
    pending_tasks = [t for t in blackboard_summary.get("tasks", []) if t["status"] == "pending"]
    
    prompt = f"""
# 角色状态
- 角色名称: {character_name}
- 饥饿度: {hunger}/100 (低于30需要进食)
- 精力: {energy}/100 (低于20需要休息)
- 当前位置: {position}
- 背包物品: {json.dumps(inventory, ensure_ascii=False)}

# 游戏世界状态
- 游戏时间: {game_state.get("GameTime", "未知")}
- 可用设施: {json.dumps(list(environment.keys()), ensure_ascii=False)}

# 黑板任务系统
- 待认领任务数: {blackboard_summary.get("pending_tasks", 0)}
- 进行中任务数: {blackboard_summary.get("active_tasks", 0)}
- 待认领任务列表:
{json.dumps(pending_tasks, ensure_ascii=False, indent=2)}

# 可用配方
{json.dumps(game_state.get("TaskRecipes", []), ensure_ascii=False, indent=2)}

# 决策指南
1. **生理需求优先**：饥饿度<30或精力<20时，优先解决生理需求
2. **协作机制**：
   - 如果需要食物但没有，可以发出"Eat"决策，系统会自动请求厨师制作
   - 如果制作物品缺原料，系统会自动发布搬运任务
   - 空闲时可以选择"CheckBlackboard"认领他人发布的任务
3. **工作任务**：根据玩家发布的任务和自身职业进行生产

# 请做出决策
返回JSON格式：
{{
    "action": "Sleep|Eat|Craft|Plant|Harvest|CheckBlackboard|Wait",
    "params": {{
        "recipe_id": 配方ID（Craft时需要）,
        "plant_id": 植物ID（Plant时需要）,
        "target_name": 目标名称（Harvest时需要）
    }},
    "reasoning": "决策理由"
}}
"""
    return prompt


def rule_based_decision(
    character_name: str,
    game_state: Dict,
    blackboard_summary: Dict
) -> Dict:
    """
    基于规则的决策（LLM不可用时的备用方案）
    """
    character_info = game_state.get("Characters", {}).get(character_name, {})
    hunger = character_info.get("Hunger", 100)
    energy = character_info.get("Energy", 100)
    skills = character_info.get("Skills", {})
    profession = character_info.get("Profession", "Unknown")
    
    # 1. 生理需求优先
    if energy < 20:
        return {
            "action": "Sleep", 
            "params": {},
            "reasoning": f"精力过低({energy:.1f}/100)，需要立即休息恢复体力"
        }
    
    if hunger < 30:
        return {
            "action": "Eat", 
            "params": {},
            "reasoning": f"饥饿度过低({hunger:.1f}/100)，需要立即进食补充能量"
        }
    
    # 2. 检查黑板任务
    pending_tasks = blackboard_summary.get("pending_tasks", 0)
    if pending_tasks > 0:
        return {
            "action": "CheckBlackboard", 
            "params": {},
            "reasoning": f"黑板上有{pending_tasks}个待认领任务，前往查看是否可以帮助其他角色"
        }
    
    # 3. 执行玩家布置的任务（根据职业和技能选择）
    recipes = game_state.get("TaskRecipes", [])
    if recipes:
        # 根据职业选择合适的配方
        suitable_recipe = None
        for recipe in recipes:
            required_facility = recipe.get("RequiredFacility", "")
            
            # Farmer -> CultivateChamber (种植)
            if profession == "Farmer" and required_facility == "CultivateChamber":
                suitable_recipe = recipe
                break
            # Crafter -> WorkStation (制作)
            elif profession == "Crafter" and required_facility == "WorkStation":
                suitable_recipe = recipe
                break
            # Chef -> Stove (烹饪)
            elif profession == "Chef" and required_facility == "Stove":
                suitable_recipe = recipe
                break
        
        # 如果没找到合适的，选第一个
        if not suitable_recipe:
            suitable_recipe = recipes[0]
        
        task_name = suitable_recipe.get("TaskName", "未知任务")
        recipe_id = suitable_recipe.get("TaskID", 1)
        required_facility = suitable_recipe.get("RequiredFacility", "")
        
        return {
            "action": "Craft",
            "params": {"recipe_id": recipe_id},
            "reasoning": f"作为{profession}，我擅长使用{required_facility}，准备执行任务：{task_name}"
        }
    
    # 4. 无事可做，等待
    return {
        "action": "Wait", 
        "params": {},
        "reasoning": "当前没有紧急任务，也没有待认领的黑板任务，暂时等待新的指令"
    }


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "ok",
        "message": "LLM Server is running",
        "timestamp": datetime.now().isoformat(),
        "llm_available": llm_client is not None
    }), 200


@app.route('/UpdateGameState', methods=['POST'])
def update_game_state():
    """
    更新游戏状态（可选接口，如果游戏不定期更新状态可以使用）
    """
    global game_state_cache
    
    try:
        data = request.get_json()
        game_state_cache = data
        
        # 定期清理旧任务
        blackboard.cleanup_old_tasks(max_age_seconds=1800)  # 30分钟
        
        return jsonify({
            "status": "success",
            "message": "Game state updated"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/GetInstruction', methods=['POST'])
def get_instruction():
    """
    获取角色的下一个指令
    这是核心接口，包含动态验证和紧急状态处理
    """
    try:
        data = request.get_json()
        
        # 解析请求
        character_name = data.get("TargetAgent", "")
        if not character_name:
            return jsonify({
                "status": "error",
                "message": "Missing TargetAgent"
            }), 400
        
        # 更新游戏状态缓存
        game_state = {
            "GameTime": data.get("GameTime", ""),
            "Environment": data.get("Environment", {}),
            "Characters": data.get("Characters", {}),
            "ItemDatabase": data.get("ItemDatabase", {}),
            "TaskRecipes": data.get("TaskRecipes", [])
        }
        
        print(f"\n{'='*60}")
        print(f"[GetInstruction] 处理 {character_name} 的指令请求")
        print(f"游戏时间: {game_state.get('GameTime')}")
        
        # 获取角色信息
        character_info = game_state.get("Characters", {}).get(character_name, {})
        hunger = character_info.get("Hunger", 100)
        energy = character_info.get("Energy", 100)
        
        # 检查紧急状态
        is_emergency = False
        emergency_reason = ""
        
        if energy < 10:
            is_emergency = True
            emergency_reason = "精力极低"
        elif hunger < 10:
            is_emergency = True
            emergency_reason = "极度饥饿"
        
        # 如果是紧急状态，清空当前计划，强制重新决策
        if is_emergency:
            remaining_steps = planner.get_remaining_steps(character_name)
            if remaining_steps > 0:
                print(f"[紧急状态] {character_name} {emergency_reason}！清空{remaining_steps}步计划，重新决策")
                planner.clear_plan(character_name)
        
        # 获取黑板摘要
        blackboard_summary = blackboard.get_summary()
        print(f"黑板任务: {blackboard_summary['pending_tasks']} 待认领, {blackboard_summary['active_tasks']} 进行中")
        print(f"角色状态: Hunger={hunger}, Energy={energy}, 剩余计划={planner.get_remaining_steps(character_name)}步")
        
        # 第一步：调用LLM做高级决策（只在需要时调用）
        # 如果队列中还有步骤，decompose_action会自动处理，不会到这里
        decision = call_llm_for_decision(character_name, game_state, blackboard_summary)
        high_level_action = decision.get("action", "Wait")
        action_params = decision.get("params", {})
        
        print(f"[高级决策] {high_level_action} - 参数: {action_params}")
        
        # 第二步：使用Planner分解为单步指令（带验证）
        next_step = planner.decompose_action(
            character_name,
            high_level_action,
            game_state,
            action_params
        )
        
        if not next_step:
            # 没有可执行的步骤，返回等待
            print(f"[Planner] 无可执行步骤，返回Wait")
            response = {
                "CharacterName": character_name,
                "CommandType": "Wait",
                "TargetName": "",
                "ParamID": 0,
                "Count": 0,
                "Decision": {
                    "action": high_level_action,
                    "params": action_params,
                    "reasoning": decision.get("reasoning", "")
                },
                "RemainingSteps": 0
            }
        else:
            print(f"[Planner] 下一步: {next_step.CommandType} -> {next_step.TargetName or next_step.ParamID}")
            # 构建返回的指令（符合FAgentCommand结构）
            response = {
                "CharacterName": character_name,
                "CommandType": next_step.CommandType,
                "TargetName": next_step.TargetName,
                "ParamID": next_step.ParamID,
                "Count": next_step.Count,
                "Decision": {
                    "action": high_level_action,
                    "params": action_params,
                    "reasoning": decision.get("reasoning", "")
                },
                "RemainingSteps": planner.get_remaining_steps(character_name)
            }
        
        print(f"[返回指令] {response}")
        print(f"{'='*60}\n")
        
        return jsonify(response), 200
        
    except Exception as e:
        import traceback
        print(f"[错误] {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/CompleteTask', methods=['POST'])
def complete_task():
    """
    标记黑板任务为完成
    """
    try:
        data = request.get_json()
        task_id = data.get("task_id", "")
        
        if blackboard.complete_task(task_id):
            return jsonify({
                "status": "success",
                "message": f"Task {task_id} completed"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": f"Task {task_id} not found"
            }), 404
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/GetBlackboard', methods=['GET'])
def get_blackboard():
    """
    获取黑板状态（调试用）
    """
    try:
        summary = blackboard.get_summary()
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    print("="*60)
    print("RimSpace LLM Server - Multi-Agent System")
    print("="*60)
    print(f"OpenAI库: {'已安装' if OPENAI_AVAILABLE else '未安装'}")
    print(f"LLM客户端: {'已初始化' if llm_client else '未初始化（将使用规则引擎）'}")
    print("="*60)
    print("\n服务器启动中...")
    print("接口列表:")
    print("  - GET  /health          : 健康检查")
    print("  - POST /GetInstruction  : 获取角色指令 [核心]")
    print("  - POST /UpdateGameState : 更新游戏状态（可选）")
    print("  - POST /CompleteTask    : 完成黑板任务")
    print("  - GET  /GetBlackboard   : 查看黑板状态（调试）")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
