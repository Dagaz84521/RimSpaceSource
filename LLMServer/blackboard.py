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
        
        # 支持嵌套字典
        value = prop.get(self.key, 0) if isinstance(prop, dict) and self.key is not None else prop
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
    def __init__ (self, description: str, goal: Goal, priority: int = 1, required_skill: Optional[str] = None):
        self.task_id = str(uuid.uuid4())
        self.description = description
        self.goal = goal
        self.priority = priority
        self.required_skill = required_skill
    
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

    def get_tasks(self, agent_info): 
        """
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
        
        

        

    
