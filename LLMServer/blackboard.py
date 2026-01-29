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
        value = prop.get(self.key) if isinstance(prop, dict) and self.key is not None else prop
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
    