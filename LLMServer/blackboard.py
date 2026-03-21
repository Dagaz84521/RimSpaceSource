'''
LLMServer 黑板模块
用于存储和管理环境中的任务和状态信息，供智能体决策使用。
'''

from typing import List, Dict, Optional, Tuple
from enum import Enum
import uuid
import os
import copy


def _disable_filtering() -> bool:
    flag = os.environ.get("RIMSPACE_BB_DISABLE_FILTER", "0").strip().lower()
    return flag in {"1", "true", "yes", "on"}

# Goal 模块
class Goal:
    def __init__(self, target_actor, property_type, key, operator, value, exclude_actor=None):
        self.target_actor = target_actor # 要检查的Actor的状态，比如"WorkStation"，"CultivateChamber_1"等
        self.property_type = property_type # 要查的那个状态，比如"Inventory", "TaskList"，"CultivateInfo"等
        self.key = key # 具体的键，比如"TaskID"，"CutivatePhase",  "ItemID"等
        self.operator = operator # 比较操作符，比如"==", "!=", ">", "<"等
        self.value = value # 目标值
        self.exclude_actor = exclude_actor # 新增：用于在计算时排除特定的 Actor
    
    def is_satisfied(self, game_state_snapshot)->bool:
        # 全局库存检查（目标对象为 "Global"时）
        if self.target_actor == "Global" and self.property_type == "Inventory":
            total = 0
            actors_list = game_state_snapshot.get("Environment", {}).get("Actors", [])
            for a in actors_list:
                if a.get("Type") == "Character": 
                    continue 
                
                # 2. 新增逻辑：如果配置了 exclude_actor，则跳过该设施的库存
                if self.exclude_actor and a.get("ActorName") == self.exclude_actor:
                    continue
                    
                inv = a.get("Inventory", {})
                if isinstance(inv, dict) and self.key is not None:
                    total += inv.get(str(self.key), 0)
            
            op = self.operator
            try:
                if op == "==": return total == self.value
                elif op == "!=": return total != self.value
                elif op == ">": return total > self.value
                elif op == "<": return total < self.value
                elif op == ">=": return total >= self.value
                elif op == "<=": return total <= self.value
                else: return False
            except Exception:
                return False

        actors_list = game_state_snapshot.get("Environment", {}).get("Actors", [])
        
        # 支持两种模式：
        # 1. 精确匹配：target_actor="CultivateChamber_1" (完全相等)
        # 2. 分类匹配：target_actor="CultivateChamber" (检查所有包含该名称的设施，汇总数值)
        
        matched_actors = []
        for actor in actors_list:
            actor_name = actor.get("ActorName", "")
            # 先尝试精确匹配
            if actor_name == self.target_actor:
                matched_actors = [actor]
                break
            # 否则尝试前缀匹配（用于分类检查）
            elif actor_name.startswith(self.target_actor):
                matched_actors.append(actor)
        
        if not matched_actors:
            return False
        
        # 如果有多个匹配的设施，汇总它们的数值
        total_value = 0
        has_numeric = False
        non_numeric_values = []
        for actor_state in matched_actors:
            prop = actor_state.get(self.property_type)
            if prop is None:
                continue
            
            # 支持嵌套字典和简单字典
            value = 0
            if isinstance(prop, dict) and self.key is not None:
                # 检查 key 是否包含"."（表示嵌套，如 "1001.count"）
                if "." in str(self.key):
                    # 处理嵌套情况：逐层获取
                    keys = str(self.key).split(".")
                    value = prop
                    for k in keys:
                        if isinstance(value, dict):
                            value = value.get(k, 0)
                        else:
                            value = 0
                            break
                else:
                    # 处理简单情况：直接按键查询
                    value = prop.get(self.key, 0)
            else:
                # 非字典属性或无 key，直接使用 prop
                value = prop
            
            # 数值用于汇总，非数值保留用于直接比较
            if isinstance(value, (int, float)):
                total_value += value
                has_numeric = True
            else:
                non_numeric_values.append(value)
        
        # 比较操作
        op = self.operator
        try:
            if has_numeric:
                if op == "==":
                    return total_value == self.value
                elif op == "!=":
                    return total_value != self.value
                elif op == ">":
                    return total_value > self.value
                elif op == "<":
                    return total_value < self.value
                elif op == ">=":
                    return total_value >= self.value
                elif op == "<=":
                    return total_value <= self.value
                else:
                    return False

            # 非数值目标仅在单一匹配时进行直接比较
            if len(non_numeric_values) != 1:
                return False
            actual_value = non_numeric_values[0]
            if op == "==":
                return actual_value == self.value
            if op == "!=":
                return actual_value != self.value
            return False
        except Exception:
            return False

    def GoalDescription(self) -> str:
        return f"Ensure {self.target_actor}'s {self.property_type}[{self.key}] {self.operator} {self.value}"

class TaskStatus(Enum):
    PENDING = "Pending"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    FAILED = "Failed"


class BlackboardTask:
    def __init__ (self, description: str, goal: Goal, preconditions: List[Goal] = None, priority: int = 1, required_skill: Optional[str] = None):
        self.task_id = str(uuid.uuid4())
        self.description = description
        self.goal = goal
        self.preconditions = preconditions or []
        self.priority = priority
        self.required_skill = required_skill
        # 可选：事件进度型任务元数据（用于“累计完成量”目标）
        self.progress_counter = None
        self.progress_target = None
        self.progress_kind = None
        self.progress_item_id = None
        self.progress_actor = None
        self.progress_actor_prefix = None
    
    def is_active(self, game_state: Dict) -> bool:
        return not self.goal.is_satisfied(game_state)
    
    def are_preconditions_met(self, game_state: Dict) -> bool:
        if not self.preconditions:
            return True  # 没有前置条件，直接返回 True
        
        for cond in self.preconditions:
            if not cond.is_satisfied(game_state):
                # 调试输出
                # print(f"    [前置条件未满足] {cond.target_actor}.{cond.property_type}[{cond.key}] {cond.operator} {cond.value}")
                return False
        return True

    def to_dict(self):
        return {
            "id": self.task_id,
            "desc": self.description,
            "prio": self.priority,
            # 不传 Goal 的细节给 LLM，除非需要，通常 LLM 只需要知道 desc 和 params
        }
class Blackboard:
    def __init__ (self):
        self.tasks: List[BlackboardTask] = []
        self.last_snapshot: Dict = {}
        self.progress_counters: Dict[str, int] = {}

    def _extract_actor_inventory(self, snapshot: Dict) -> Dict[str, Dict[str, int]]:
        actor_inv: Dict[str, Dict[str, int]] = {}
        env = snapshot.get("Environment", {}) if isinstance(snapshot, dict) else {}
        actors = env.get("Actors", []) if isinstance(env, dict) else []
        if isinstance(actors, dict):
            actors = list(actors.values())

        if not isinstance(actors, list):
            return actor_inv

        for actor in actors:
            if not isinstance(actor, dict):
                continue
            name = actor.get("ActorName")
            inv = actor.get("Inventory", {})
            if not name or not isinstance(inv, dict):
                continue
            safe_inv: Dict[str, int] = {}
            for key, value in inv.items():
                if isinstance(value, int):
                    safe_inv[str(key)] = value
            actor_inv[str(name)] = safe_inv
        return actor_inv

    def _inventory_deltas(self, prev_snapshot: Dict, curr_snapshot: Dict) -> List[Tuple[str, str, int]]:
        prev = self._extract_actor_inventory(prev_snapshot)
        curr = self._extract_actor_inventory(curr_snapshot)
        deltas: List[Tuple[str, str, int]] = []

        actor_names = set(prev.keys()) | set(curr.keys())
        for actor_name in actor_names:
            prev_inv = prev.get(actor_name, {})
            curr_inv = curr.get(actor_name, {})
            item_ids = set(prev_inv.keys()) | set(curr_inv.keys())
            for item_id in item_ids:
                delta = curr_inv.get(item_id, 0) - prev_inv.get(item_id, 0)
                if delta > 0:
                    deltas.append((actor_name, item_id, delta))
        return deltas

    def _match_progress_def(self, pdef: Dict, actor_name: str, item_id: str) -> bool:
        if str(pdef.get("item_id")) != str(item_id):
            return False

        actor_exact = pdef.get("actor")
        actor_prefix = pdef.get("actor_prefix")
        if actor_exact:
            return actor_name == actor_exact
        if actor_prefix:
            return actor_name.startswith(actor_prefix)
        return True

    def _accumulate_progress(self, prev_snapshot: Dict, curr_snapshot: Dict) -> None:
        # 只为当前任务中声明了 progress_counter 的任务累计进度
        progress_defs: Dict[str, Dict] = {}
        for task in self.tasks:
            counter = getattr(task, "progress_counter", None)
            if not counter:
                continue
            if counter in progress_defs:
                continue
            progress_defs[counter] = {
                "kind": getattr(task, "progress_kind", None),
                "item_id": str(getattr(task, "progress_item_id", "")),
                "actor": getattr(task, "progress_actor", None),
                "actor_prefix": getattr(task, "progress_actor_prefix", None),
            }

        if not progress_defs:
            return

        deltas = self._inventory_deltas(prev_snapshot, curr_snapshot)
        for actor_name, item_id, delta in deltas:
            for counter, pdef in progress_defs.items():
                if self._match_progress_def(pdef, actor_name, item_id):
                    self.progress_counters[counter] = self.progress_counters.get(counter, 0) + int(delta)

    def _is_progress_task_done(self, task: BlackboardTask) -> bool:
        counter = getattr(task, "progress_counter", None)
        target = getattr(task, "progress_target", None)
        if not counter or target is None:
            return False
        return self.progress_counters.get(counter, 0) >= int(target)

    def post_task(self, task: BlackboardTask):
        # 避免重复任务
        for t in self.tasks:
            g = t.goal
            if (g.target_actor == task.goal.target_actor and
                g.property_type == task.goal.property_type and
                g.key == task.goal.key and
                g.operator == task.goal.operator and
                g.value == task.goal.value):
                # 重复目标任务沿用原实例，但刷新描述与动态参数，避免 source/destination 过期
                t.description = task.description
                for field in (
                    "item_id", "source", "destination", "count",
                    "progress_counter", "progress_target", "progress_kind",
                    "progress_item_id", "progress_actor", "progress_actor_prefix",
                ):
                    if hasattr(task, field):
                        setattr(t, field, getattr(task, field))
                return t  # 返回已存在的任务实例
        self.tasks.append(task)
        print(f"[Blackboard] 新任务已添加: {task.description}")
        return task  # 返回新添加的任务实例
    
    def update(self, game_state: Dict):
        """
        【关键逻辑】
        每回合调用。检查所有任务的 Goal。
        如果 Goal 已经满足 (is_satisfied == True)，则移除任务。
        """
        if self.last_snapshot:
            self._accumulate_progress(self.last_snapshot, game_state)

        active_tasks = []
        for t in self.tasks:
            if self._is_progress_task_done(t):
                counter = getattr(t, "progress_counter", "")
                current = self.progress_counters.get(counter, 0)
                target = getattr(t, "progress_target", 0)
                print(f"[Blackboard] 进度已达成，自动移除: {t.description} ({current}/{target})")
            elif t.goal.is_satisfied(game_state):
                print(f"[Blackboard] 需求已满足，自动移除: {t.description}")
            else:
                active_tasks.append(t)
        self.tasks = active_tasks
        self.last_snapshot = copy.deepcopy(game_state) if isinstance(game_state, dict) else {}

    def get_executable_tasks(self, agent_info, game_state: Dict) -> List[BlackboardTask]:
        """
        获取当前可执行的任务列表（无未完成依赖 + 符合技能要求）
        :param agent_info: 角色信息，主要是角色的技能
        :param game_state: 游戏状态，可能是 {"Environment": {...}} 或 {"Actors": [...]} 格式
        :return: 可执行的任务列表
        """
        if _disable_filtering():
            return list(self.tasks)

        # 提取角色信息
        char_name = agent_info.get("CharacterName", "Unknown")
        
        # 提取角色技能 (兼容 Skills 和 CharacterSkills，处理大小写)
        raw_skills = agent_info.get("Skills", []) or agent_info.get("CharacterSkills", [])
        agent_skills = {s.lower() for s in raw_skills}
        
        # print(f"[get_executable_tasks] {char_name} 的技能: {agent_skills}, 黑板任务数: {len(self.tasks)}")
        
        # 包装环境数据以符合 Goal.is_satisfied 的期望格式
        wrapped_state = {"Environment": game_state} if "Environment" not in game_state else game_state
        
        # 构建当前存在的任务ID集合        
        executable_tasks = []
        for t in self.tasks:
            # 1. 检查技能要求
            required = t.required_skill
            if required is not None and required.lower() not in agent_skills:
                # print(f"  [跳过] {t.description[:50]}... (技能不匹配: 需要 {required})")
                continue
            
            # 2. 检查先决条件 (传入当前真实游戏状态进行验证)
            if not t.are_preconditions_met(wrapped_state):
                # print(f"  [跳过] {t.description[:50]}... (前置条件未满足)")
                continue
            
            # print(f"  [可执行] {t.description[:50]}...")
            executable_tasks.append(t)
        
        # print(f"[get_executable_tasks] {char_name} 可执行任务数: {len(executable_tasks)}")
        return executable_tasks
    
    def get_tasks(self, agent_info): 
        """
        【已废弃】请使用 get_executable_tasks() 替代
        获取任务列表，可选按任务类型和请求者（角色）筛选。
        :param agent_info: 角色信息，主要是角色的技能，根据角色的技能筛选任务
        :return: 满足条件的任务列表
        """
        # 提取角色技能 (兼容 Skills 和 CharacterSkills，处理大小写)
        raw_skills = agent_info.get("Skills", []) or agent_info.get("CharacterSkills", [])
        agent_skills = {s.lower() for s in raw_skills}

        suitable_tasks = []
        for t in self.tasks:
            if t.required_skill is None or t.required_skill.lower() in agent_skills:
                suitable_tasks.append(t)
        return suitable_tasks
        
        

        

    
