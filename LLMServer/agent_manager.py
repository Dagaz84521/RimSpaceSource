# agent_manager.py
from config import SYSTEM_PROMPT_TEMPLATE, THRESHOLDS
from llm_client import LLMClient
from planner import Planner
import os
import re


def _llm_visible_task_source() -> str:
    # all | perceiver
    return os.environ.get("RIMSPACE_LLM_TASK_SOURCE", "all").strip().lower()


def _is_perceiver_task(task) -> bool:
    return str(getattr(task, "source", "")).strip().lower() == "perceiver"


def _is_no_blackboard_mode() -> bool:
    return os.environ.get("RIMSPACE_ABLATION_MODE", "full").strip().lower() == "no_blackboard"


def _format_failure_feedback_for_mode(feedback: str) -> str:
    """Keep full-mode feedback untouched; simplify no_blackboard feedback to pure failure reasons."""
    if not _is_no_blackboard_mode():
        return feedback

    text = str(feedback or "").strip()

    # Remove planner-side supply wording in no_blackboard ablation.
    text = text.replace("System supply tasks initiated. Please Wait.", "Execution failed.")
    text = text.replace("Please Wait.", "")
    text = text.replace("System supply tasks initiated.", "")

    # Normalize duplicated spaces/punctuation after replacements.
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+\.", ".", text)

    if not text:
        text = "Execution failed."
    return text


def _extract_missing_resource_names(feedback: str):
    text = str(feedback or "")
    match = re.search(r"Resources Missing:\s*([^\.]+)", text, flags=re.IGNORECASE)
    if not match:
        return []
    raw = match.group(1)
    names = [p.strip() for p in raw.split(",") if p.strip()]
    return names


def _normalize_skill_name(skill_name: str) -> str:
    s = str(skill_name or "").strip().lower()
    if s.startswith("can"):
        return s
    return f"can{s}"

class RimSpaceAgent:
    def __init__(self, name, profession, blackboard_instance):
        self.name = name
        self.profession = profession
        self.llm = LLMClient()

        #初始化规划器和动作队列
        self.blackboard = blackboard_instance
        self.planner = Planner(self.blackboard)
        self.action_queue = []
        self.feedback_buffer = ""
        self.last_decision_context = {}  # 存储上一次LLM决策的上下文
        
        # 内部 D2A 状态 (0-100)
        self.desires = {
            "hunger": 0,
            "exhaustion": 0,
            "duty": 0
        }

    def update_state(self, char_data, environment_data):
        """
        核心步骤：将游戏数据映射为 D2A 欲望值
        """
        # 1. 映射生理欲望
        # 假设游戏里 Energy 是 100-0 (100最精神)，我们需要反转为 Exhaustion 0-100 (100最累)
        game_energy = char_data.get("CharacterStats", {}).get("Energy", 100)
        self.desires["exhaustion"] = max(0, 100 - game_energy)
        
        # 假设游戏里 Hunger 是 0-100 (100最饱)，我们需要反转为 Hunger Desire 0-100 (100最饿)
        game_food = char_data.get("CharacterStats", {}).get("Hunger", 100)
        self.desires["hunger"] = max(0, 100 - game_food)

        # 2. 映射社会欲望 (Sense of Duty)
        # 简单逻辑：每个任务增加 20 点压力
        task_count = len(self._get_visible_tasks(char_data, environment_data))
        self.desires["duty"] = min(100, task_count * 20)
        #print(f"[状态更新] {self.name} - Hunger: {self.desires['hunger']}, Exhaustion: {self.desires['exhaustion']}, Duty: {self.desires['duty']}")

    def generate_observation_text(self, char_data, environment_data):
        """生成给 LLM 看的自然语言描述"""
        h = self.desires["hunger"]
        e = self.desires["exhaustion"]
        d = self.desires["duty"]
        
        status_text = f"""
        [Current Desires]
        - Hunger: {h}/100 ({'CRITICAL' if h > 70 else 'Normal'})
        - Exhaustion: {e}/100 ({'Sleepy' if e > 70 else 'Fresh'})
        - Sense of Duty: {d}/100 ({'Guilty' if d > 50 else 'Relaxed'})
        """
        
        # 获取任务列表字符串 (修正：从服务器端 Blackboard 获取，而不是从请求数据中获取)
        relevant_tasks = self._get_visible_tasks(char_data, environment_data)
        tasks = [self._format_task_for_prompt(t, environment_data) for t in relevant_tasks]
        env_text = f"\n[Task Blackboard]: {', '.join(tasks) if tasks else 'Empty'}"

        transport_hint = self._build_transport_constraint_hint(environment_data)
        if transport_hint:
            env_text += f"\n[Transport Constraint]: {transport_hint}"
        
        # Planner 反馈信息
        if self.feedback_buffer:
            env_text += f"\n[Planner Feedback]: {self.feedback_buffer}"
            self.feedback_buffer = ""  # 清空反馈缓冲区

        if _is_no_blackboard_mode():
            hint = self._build_no_blackboard_recipe_hint(char_data)
            if hint:
                env_text += f"\n[Recipe Hints]: {hint}"

        return status_text + env_text

    def _build_transport_constraint_hint(self, environment_data):
        """Explain that transportability depends on source inventory, not cultivate phase."""
        actors = environment_data.get("Actors", [])
        if not isinstance(actors, list):
            return ""

        pending_harvest = []
        for actor in actors:
            actor_name = actor.get("ActorName", "")
            if "CultivateChamber" not in actor_name:
                continue

            cultivate_info = actor.get("CultivateInfo", {})
            phase = cultivate_info.get("CurrentPhase", "")
            inventory = actor.get("Inventory", {}) if isinstance(actor.get("Inventory", {}), dict) else {}
            has_items = any((isinstance(v, int) and v > 0) for v in inventory.values())

            if phase == "ECultivatePhase::ECP_ReadyToHarvest" and not has_items:
                pending_harvest.append(actor_name)

        if not pending_harvest:
            return (
                "Transport is valid only when source inventory has item count > 0. "
                "Cultivate phase alone is not enough."
            )

        sample = ", ".join(pending_harvest[:3])
        if len(pending_harvest) > 3:
            sample += ", ..."
        return (
            "Transport is valid only when source inventory has item count > 0. "
            f"{sample} are ReadyToHarvest but inventory is empty; Farmer must Harvest first."
        )

    def _get_agent_skills(self, char_data):
        raw_skills = char_data.get("Skills", []) or char_data.get("CharacterSkills", [])
        skills = {_normalize_skill_name(s) for s in raw_skills}
        if skills:
            return skills

        # 回退: 某些输入缺失技能字段时，按职业推断
        role = str(self.profession or "").strip().lower()
        if role == "farmer":
            return {"canfarm"}
        if role == "crafter":
            return {"cancraft"}
        if role == "chef":
            return {"cancook"}
        return set()

    def _build_no_blackboard_recipe_hint(self, char_data):
        skills = self._get_agent_skills(char_data)
        hints = []
        if "cancraft" in skills:
            hints.append("Thread <- Cotton x1 (Craft Thread at WorkStation)")
            hints.append("Cloth <- Cotton x1 (Craft Cloth at WorkStation)")
            hints.append("Coat <- Cloth x1 + Thread x1 (Craft Coat at WorkStation)")
        if "cancook" in skills:
            hints.append("Meal <- Corn x1 (Craft Meal at Stove)")
        return "; ".join(hints)

    def _build_missing_resource_guidance(self, formatted_feedback: str, char_data) -> str:
        if not _is_no_blackboard_mode():
            return ""

        missing_names = _extract_missing_resource_names(formatted_feedback)
        if not missing_names:
            return ""

        skills = self._get_agent_skills(char_data)
        name_to_id = {
            str(v).strip().lower(): str(k)
            for k, v in self.planner.game_data.item_name_to_id.items()
        }
        item_map = self.planner.game_data.item_map
        recipe_map = self.planner.game_data.product_to_recipe

        suggestions = []
        for name in missing_names:
            item_id = name_to_id.get(str(name).strip().lower())
            if not item_id:
                continue

            recipe = recipe_map.get(str(item_id))
            if not recipe:
                continue

            required = {_normalize_skill_name(k) for k, v in recipe.get("RequiredSkill", {}).items() if v}
            if required and skills.isdisjoint(required):
                continue

            ingredients = recipe.get("Ingredients", [])
            if ingredients:
                ing_desc = []
                for ing in ingredients:
                    ing_id = str(ing.get("ItemID"))
                    ing_name = item_map.get(ing_id, {}).get("ItemName", ing_id)
                    ing_count = ing.get("Count", 1)
                    ing_desc.append(f"{ing_name} x{ing_count}")
                ingredient_text = ", ".join(ing_desc)
            else:
                ingredient_text = "no ingredients"

            suggestions.append(f"If capable, craft {name} first (needs: {ingredient_text}).")

        if not suggestions:
            return ""
        return " ".join(suggestions)

    def _resolve_item_id(self, item_name):
        raw = str(item_name or "").strip()
        if not raw:
            return None

        # 先尝试精确命中 ItemName（英文）
        direct = self.planner.game_data.item_name_to_id.get(raw)
        if direct is not None:
            return direct

        lower_raw = raw.lower()

        # 兼容常见英文小写别名
        english_alias = {
            "cotton": "Cotton",
            "corn": "Corn",
            "thread": "Thread",
            "cloth": "Cloth",
            "meal": "Meal",
            "coat": "Coat",
        }
        aliased = english_alias.get(lower_raw)
        if aliased:
            hit = self.planner.game_data.item_name_to_id.get(aliased)
            if hit is not None:
                return hit

        # 兼容显示名（中文）
        for item in self.planner.game_data.items:
            if str(item.get("DisplayName", "")).strip() == raw:
                return item.get("ItemID")

        return None

    def generate_world_state(self, environment_data):
        """生成当前世界状态信息，显示各个地点的物品库存"""
        world_state = "\n【各地点物品库存】\n"
        
        try:
            actors = environment_data.get("Actors", [])
            
            for actor in actors:
                actor_name = actor.get("ActorName", "Unknown")
                inventory = actor.get("Inventory", {})
                
                # 跳过空库存的地点，除非是重要地点（如Storage、Stove）
                if not inventory and actor_name not in ["Storage", "Stove", "WorkStation"]:
                    continue
                
                # 格式化库存信息
                if inventory:
                    item_list = []
                    for item_id, count in inventory.items():
                        # 从itemid_to_name映射获取物品名称
                        item_name = self._get_item_name(item_id)
                        item_list.append(f"{item_name}({item_id}): {count}件")
                    
                    world_state += f"  - {actor_name}: {', '.join(item_list)}\n"
                else:
                    world_state += f"  - {actor_name}: 【空】\n"
            
            # 添加培养舱的状态
            world_state += "\n【培养舱状态】\n"
            for actor in actors:
                actor_name = actor.get("ActorName", "")
                if "CultivateChamber" in actor_name:
                    cultivate_info = actor.get("CultivateInfo", {})
                    current_phase = cultivate_info.get("CurrentPhase", "Unknown")
                    cultivate_type = cultivate_info.get("TargetCultivateType", "None")
                    growth_progress = cultivate_info.get("GrowthProgress", 0)
                    growth_max = cultivate_info.get("GrowthMaxProgress", 24)
                    
                    phase_display = self._parse_phase(current_phase)
                    crop_name = self._parse_cultivate_type(cultivate_type)

                    chamber_inventory = actor.get("Inventory", {}) if isinstance(actor.get("Inventory", {}), dict) else {}
                    chamber_total = sum(v for v in chamber_inventory.values() if isinstance(v, int) and v > 0)
                    transport_state = "可搬运" if chamber_total > 0 else "无库存(不可搬运)"

                    world_state += (
                        f"  - {actor_name}: [{phase_display}] {crop_name} "
                        f"(进度: {growth_progress}/{growth_max}, 仓内库存: {chamber_total}, {transport_state})\n"
                    )
            
            return world_state
        except Exception as e:
            return f"【世界状态获取失败】: {str(e)}"

    def _get_item_name(self, item_id):
        """根据物品ID获取物品名称"""
        item_id_str = str(item_id)
        # 简单的ID到名称的映射
        item_names = {
            "1001": "棉花(Cotton)",
            "1002": "玉米(Corn)",
            "2001": "棉线(Thread)",
            "2002": "布料(Cloth)",
            "2003": "套餐(Meal)",
            "3001": "衣服(Coat)"
        }
        return item_names.get(item_id_str, f"物品({item_id})")

    def _parse_phase(self, phase_str):
        """解析培养舱的生长阶段"""
        phase_map = {
            "ECultivatePhase::ECP_WaitingToPlant": "等待种植",
            "ECultivatePhase::ECP_Growing": "生长中",
            "ECultivatePhase::ECP_ReadyToHarvest": "准备收获"
        }
        return phase_map.get(phase_str, phase_str)

    def _parse_cultivate_type(self, cultivate_type_str):
        """解析作物类型"""
        type_map = {
            "ECultivateType::ECT_Cotton": "棉花",
            "ECultivateType::ECT_Corn": "玉米",
            "ECultivateType::ECT_None": "无"
        }
        return type_map.get(cultivate_type_str, cultivate_type_str)

    def _format_task_for_prompt(self, task, environment_data=None):
        """为 LLM 格式化任务描述，必要时补充参数和前置条件信息"""
        desc = task.description
        
        # 补充参数信息 (Transport 任务)
        if "Transport" in desc and hasattr(task, "item_id"):
            item_id = getattr(task, "item_id", "")
            count = getattr(task, "count", "")
            source = getattr(task, "source", "")
            destination = getattr(task, "destination", "")
            desc += f" [item_id={item_id}, count={count}, source={source}, destination={destination}]"
        
        # 补充前置条件信息
        if hasattr(task, "preconditions") and task.preconditions and environment_data:
            unmet_conditions = []
            for cond in task.preconditions:
                wrapped_env = {"Environment": environment_data} if "Environment" not in environment_data else environment_data
                if not cond.is_satisfied(wrapped_env):
                    cond_str = f"{cond.target_actor}.{cond.property_type}[{cond.key}] {cond.operator} {cond.value}"
                    unmet_conditions.append(cond_str)
            
            if unmet_conditions:
                desc += f" [Preconditions-Unmet: {', '.join(unmet_conditions)}]"
            else:
                desc += " [Preconditions-OK]"
        elif hasattr(task, "preconditions") and task.preconditions:
            desc += f" [Preconditions: {len(task.preconditions)} items]"
        
        return desc

    def _get_visible_tasks(self, char_data, environment_data):
        tasks = self.blackboard.get_executable_tasks(char_data, environment_data)
        if _llm_visible_task_source() == "perceiver":
            tasks = [t for t in tasks if _is_perceiver_task(t)]
        return tasks

    def make_decision(self, char_data, environment_data):
        """主决策循环"""
        
        # 0. 始终先更新状态 (确保每一帧的状态都是最新的，即使在执行队列中)
        self.update_state(char_data, environment_data)

        # 1. 检查并执行动作队列
        if self.action_queue:
            next_cmd = self.action_queue.pop(0)
            
            # [修正] 补全指令信息
            next_cmd["CharacterName"] = self.name
            
            # [修正] 确保后续动作也携带原始决策信息，防止前端UI显示空白
            if "Decision" not in next_cmd:
                next_cmd["Decision"] = self.last_decision_context
            
            # [优化] 添加剩余步数信息 (可选)
            next_cmd["RemainingSteps"] = len(self.action_queue)

            # print(f"[{self.name}] Executing queued action: {next_cmd.get('CommandType')} (Left: {len(self.action_queue)})")
            # print(f"[{self.name}] Remaining action_queue: {self.action_queue}")
            return next_cmd

        # 2. 构建 Prompt
        specific_profile = self.load_profile(self.profession)
        world_state = self.generate_world_state(environment_data)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            profession=self.profession,
            name=self.name,
            specific_profile=specific_profile,
            world_state=world_state
        )
        user_context = self.generate_observation_text(char_data, environment_data)
        
        # 3. 调用 LLM
        # print(f"[{self.name}] Thinking...")
        response_str = self.llm.query(system_prompt, user_context)
        decision_json = self.llm.parse_json_response(response_str)
        
        # [修正] 安全获取 command，防止 None
        command_type = decision_json.get("command", "Wait") # 默认为 Wait
        if not isinstance(command_type, str):
            command_type = "Wait"

        # 4. 调用 Planner 进行规划
        # 将 decision_json 直接作为 params 传入
        decision_json["current_location"] = char_data.get("CurrentLocation")
        
        # 【新增】如果是 Transport 命令，桥接 LLM 字段到 Planner 参数
        if command_type == "Transport":
            # 1) 优先使用 LLM 已给出的字段
            if not decision_json.get("target_name") and decision_json.get("source"):
                decision_json["target_name"] = decision_json.get("source")

            if not decision_json.get("aux_name") and decision_json.get("destination"):
                decision_json["aux_name"] = decision_json.get("destination")

            if decision_json.get("item_id") in (None, "", 0):
                resolved_item_id = self._resolve_item_id(decision_json.get("item_name"))
                if resolved_item_id is not None:
                    decision_json["item_id"] = resolved_item_id

            # 2) 若仍缺失，再尝试从黑板运输任务补齐
            # 从黑板中找到相关的搬运任务，提取 item_id, source, destination（不再需要count）
            relevant_tasks = self.blackboard.get_executable_tasks(char_data, environment_data)
            transport_task = next((t for t in relevant_tasks if "Transport" in t.description), None)
            
            if transport_task and hasattr(transport_task, 'item_id'):
                # 仅补缺，不覆盖 LLM 已给出的参数
                if decision_json.get("item_id") in (None, "", 0):
                    decision_json["item_id"] = transport_task.item_id
                if not decision_json.get("target_name"):
                    decision_json["target_name"] = transport_task.source
                if not decision_json.get("aux_name"):
                    decision_json["aux_name"] = transport_task.destination
        
        plan_result = self.planner.generate_plan(self.name, command_type, decision_json, environment_data)
        
        if plan_result.success:
            # 规划成功
            self.action_queue = plan_result.plan
            
            # [修正] 保存当前的决策上下文，供队列中后续动作使用
            self.last_decision_context = decision_json
            
            if self.action_queue:
                first_cmd = self.action_queue.pop(0)
                first_cmd["CharacterName"] = self.name
                first_cmd["Decision"] = decision_json # 附带决策信息
                first_cmd["RemainingSteps"] = len(self.action_queue)
                return first_cmd
            else:
                # 极其罕见的情况：成功但没有动作
                return {
                    "CharacterName": self.name, 
                    "CommandType": "Wait", 
                    "TargetName": "",
                    "ParamID": 1, 
                    "Count": 0, 
                    "Decision": decision_json,
                    "RemainingSteps": 0
                }
        else:
            # 规划失败（如资源不足，Planner已自动发布任务）
            # print(f"[{self.name}] Plan Failed: {plan_result.feedback}")
            formatted_feedback = _format_failure_feedback_for_mode(plan_result.feedback)
            guidance = self._build_missing_resource_guidance(formatted_feedback, char_data)
            if guidance:
                formatted_feedback = f"{formatted_feedback} {guidance}"
            self.feedback_buffer = f"Last Action '{command_type}' Failed: {formatted_feedback}"
            
            # 返回 Wait 并附带失败原因
            # [优化] 这里的 Decision 需要反映出失败状态
            failure_decision = decision_json.copy()
            # 保留原有reasoning，追加失败信息
            original_reasoning = failure_decision.get("reasoning", "")
            failure_decision["reasoning"] = f"{original_reasoning}\n[Planner Failed]: {formatted_feedback}"
            
            return {
                "CharacterName": self.name, 
                "CommandType": "Wait",
                "TargetName": "", 
                "ParamID": 2, 
                "Count": 0,
                "Decision": failure_decision,
                "RemainingSteps": 0
            }
    
    def load_profile(self, profession):
        """从文档库加载特定职业的背景故事"""
        # 构建文件路径: LLMServerNew/../文档/profile_{profession}.txt
        current_dir = os.path.dirname(__file__)  # LLMServerNew 目录
        parent_dir = os.path.dirname(current_dir)  # Source 目录
        profile_dir = os.path.join(parent_dir, "Docs")
        profile_file = os.path.join(profile_dir, f"profile_{profession.lower()}.txt")
        
        # 读取文件内容
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            # print(f"Warning: Profile file not found: {profile_file}")
            return f"A skilled {profession} in the RimSpace colony."
        except Exception as e:
            # print(f"Error loading profile: {e}")
            return f"A skilled {profession} in the RimSpace colony."