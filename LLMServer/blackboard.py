'''
LLMServer 黑板模块
用于存储和管理环境中的任务和状态信息，供智能体决策使用。
'''

from typing import List, Dict, Optional
from enum import Enum
import uuid

# Goal 模块
class Goal:
    def __init__(self, target_actor, property_type, key, operator, value):
        self.target_actor = target_actor # 要检查的Actor的状态，比如"WorkStation"，"CultivateChamber_1"等
        self.property_type = property_type # 要查的那个状态，比如"Inventory", "TaskList"，"CultivateInfo"等
        self.key = key # 具体的键，比如"TaskID"，"CutivatePhase",  "ItemID"等
        self.operator = operator # 比较操作符，比如"==", "!=", ">", "<"等
        self.value = value # 目标值
    
    def is_satisfied(self, game_state_snapshot)->bool:
        actors_list = game_state_snapshot.get("Environment", {}).get("Actors", [])
        actor_state = next((a for a in actors_list if a.get("ActorName") == self.target_actor), None)
        if not actor_state:
            return False
        
        prop = actor_state.get(self.property_type)
        if prop is None:
            return False
        
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
        
        # 比较操作
        op = self.operator
        try:
            if op == "==":
                return value == self.value
            elif op == "!=":
                return value != self.value
            elif op == ">":
                return value > self.value
            elif op == "<":
                return value < self.value
            elif op == ">=":
                return value >= self.value
            elif op == "<=":
                return value <= self.value
            else:
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
    def __init__ (self, description: str, goal: Goal, priority: int = 1, required_skill: Optional[str] = None, dependencies: List[str] = None):
        self.task_id = str(uuid.uuid4())
        self.description = description
        self.goal = goal
        self.priority = priority
        self.required_skill = required_skill
        self.dependencies = dependencies or []  # 依赖的其他任务的task_id列表
    
    def is_active(self, game_state: Dict) -> bool:
        return not self.goal.is_satisfied(game_state)

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

    def post_task(self, task: BlackboardTask):
        # 避免重复任务
        for t in self.tasks:
            g = t.goal
            if (g.target_actor == task.goal.target_actor and
                g.property_type == task.goal.property_type and
                g.key == task.goal.key and
                g.operator == task.goal.operator and
                g.value == task.goal.value):
                print(f"[Blackboard] 任务已存在，跳过添加: {task.description}")
                return
        self.tasks.append(task)
        print(f"[Blackboard] 新任务已添加: {task.description}")
    
    def update(self, game_state: Dict):
        """
        【关键逻辑】
        每回合调用。检查所有任务的 Goal。
        如果 Goal 已经满足 (is_satisfied == True)，则移除任务。
        """
        active_tasks = []
        for t in self.tasks:
            if t.goal.is_satisfied(game_state):
                print(f"[Blackboard] 需求已满足，自动移除: {t.description}")
            else:
                active_tasks.append(t)
        self.tasks = active_tasks

    def get_executable_tasks(self, agent_info):
        """
        获取当前可执行的任务列表（无未完成依赖 + 符合技能要求）
        :param agent_info: 角色信息，主要是角色的技能
        :return: 可执行的任务列表
        """
        # 提取角色技能 (兼容 Skills 和 CharacterSkills，处理大小写)
        raw_skills = agent_info.get("Skills", []) or agent_info.get("CharacterSkills", [])
        agent_skills = {s.lower() for s in raw_skills}
        
        # 构建当前存在的任务ID集合
        active_task_ids = {t.task_id for t in self.tasks}
        
        executable_tasks = []
        for t in self.tasks:
            # 检查技能要求
            if t.required_skill is not None and t.required_skill.lower() not in agent_skills:
                continue
            
            # 检查依赖关系：所有依赖的任务都必须已完成（不在active列表中）
            has_unmet_dependencies = any(dep_id in active_task_ids for dep_id in t.dependencies)
            if has_unmet_dependencies:
                continue
            
            executable_tasks.append(t)
        
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
        
        

        

    
