import json
import os
import uuid
from typing import List, Dict, Any, Optional, Tuple
from blackboard import Goal, BlackboardTask
from game_data_manager import GameDataManager

# === 基础指令构造函数 ===
def cmd_move(target): return {"CommandType": "Move", "TargetName": target, "ParamID": 0, "Count": 0}
def cmd_take(item_id, count): return {"CommandType": "Take", "TargetName": "", "ParamID": int(item_id), "Count": int(count)}
def cmd_put(item_id, count): return {"CommandType": "Put", "TargetName": "", "ParamID": int(item_id), "Count": int(count)}
def cmd_use(param_id): return {"CommandType": "Use", "TargetName": "", "ParamID": int(param_id), "Count": 0}
def cmd_wait(minutes): return {"CommandType": "Wait", "TargetName": "", "ParamID": int(minutes), "Count": 0}

class PlanResult:
    """规划结果封装，包含动作序列或失败反馈"""
    def __init__(self, success: bool, plan: List[Dict] = None, feedback: str = ""):
        self.success = success
        self.plan = plan if plan else []
        self.feedback = feedback



class Planner:
    def __init__(self, blackboard_instance):
        self.blackboard = blackboard_instance
        self.game_data = GameDataManager()

        # 转发属性以便兼容
        self.items = self.game_data.items
        self.tasks = self.game_data.tasks
        self.item_map = self.game_data.item_map
        self.task_map = self.game_data.task_map
        self.item_name_to_id = self.game_data.item_name_to_id
        self.product_to_recipe = self.game_data.product_to_recipe
    
    def get_total_item_count(self, item_id, environment) -> int:
        """""计算环境中某种物品的总量 (Storage + 各种容器)"""
        total = 0
        actors = environment.get("Actors", [])
        str_id = str(item_id)
        for actor in actors:
            # 排除掉 Agent 自己的背包 (防止死锁计算)
            if actor.get("Type") == "Character": 
                continue
                
            inv = actor.get("Inventory", {})
            if isinstance(inv, dict):
                item_data = inv.get(str_id)
                if item_data:
                    total += item_data.get("count", 0)
        return total
    
    def find_actor_with_item(self, item_id, min_count, environment) -> str:
        """寻找拥有指定数量物品的最佳容器"""
        str_id = str(item_id)
        actors = environment.get("Actors", [])
        
        # 优先查找 Storage
        for actor in actors:
            if "Storage" in actor.get("ActorType", ""):
                inv = actor.get("Inventory", {})
                if isinstance(inv, dict):
                    data = inv.get(str_id)
                    if data and data.get("count", 0) >= min_count:
                        return actor.get("ActorName")
        
        # 其次查找任意容器
        for actor in actors:
            inv = actor.get("Inventory", {})
            if isinstance(inv, dict):
                data = inv.get(str_id)
                if data and data.get("count", 0) >= min_count:
                    return actor.get("ActorName")
        return None
    
    def find_actor_by_type(self, type_suffix, environment) -> str:
        """寻找特定类型的设施 (如 'Stove', 'WorkStation')"""
        if not type_suffix: return None
        actors = environment.get("Actors", [])
        for actor in actors:
            # 简单的名称匹配或类型匹配
            if type_suffix in actor.get("ActorType", "") or type_suffix in actor.get("ActorName", ""):
                return actor.get("ActorName")
        return None
    
    # === 核心入口 ===
    def generate_plan(self, agent_name, high_level_action, params, environment):
        """
        根据高层指令生成动作序列。
        如果资源不足，会自动触发系统任务并返回失败反馈。
        """
        method_name = f"_plan_{high_level_action.lower()}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(agent_name, params, environment)
        else:
            return PlanResult(False, [cmd_wait(2)], feedback=f"未知的高层指令: {high_level_action}")
        
    # === 各类高层指令的规划实现 ===
    def _plan_eat(self, agent_name, params, env) -> PlanResult:
        # 寻找食物（Meal -> 2003)
        food_id = 2003
        source = self.find_actor_with_item(food_id, 1, env)
        if not source:
            # 游戏中没有食物，触发系统任务
            # 补充3个食物，根据游戏内设定，刚好满足殖民地所有人的进餐需求
            self._trigger_system_supply(food_id, 3)
            return PlanResult(False, [cmd_wait(5)], "No food available. Cooking task posted.")
        plan = []
        plan.append(cmd_move(source))
        plan.append(cmd_take(food_id, 1))
        table = self.find_actor_by_type("Table", env)
        if table:
            plan.append(cmd_move(table))
        plan.append(cmd_use(food_id))
        return PlanResult(True, plan, "Eating sequence")
    
    def _plan_plant(self, agent_name, params, env) -> PlanResult:
        target = params.get("target_name")
        if not target:
            return PlanResult(False, [cmd_wait(2)], "No target specified for planting.")
        return PlanResult(True, [cmd_move(target), cmd_use(0)], "Planting sequence")
    
    def _plan_harvest(self, agent_name, params, env) -> PlanResult:
        target = params.get("target_name")
        if not target:
            return PlanResult(False, [cmd_wait(2)], "No target specified for harvesting.")
        return PlanResult(True, [cmd_move(target), cmd_use(0)], "Harvesting sequence")
    
    def _plan_transport(self, agent_name, params, env) -> PlanResult:
        source = params.get("target_name")
        destination = params.get("aux_name")
        item_id = params.get("item_id")
        count = params.get("count", 1)
        if not source or not destination or not item_id:
            return PlanResult(False, [cmd_wait(2)], "Incomplete parameters for transport.")
        return PlanResult(True, [
            cmd_move(source),
            cmd_take(item_id, count),
            cmd_move(destination),
            cmd_put(item_id, count)
        ], f"Transporting {count} items.")
    
    def _plan_wait(self, agent_name, params, env) -> PlanResult:
        minutes = params.get("minutes", 10)
        return PlanResult(True, [cmd_wait(minutes)], f"Waiting for {minutes} minutes.")
    
    def _plan_craft(self, agent_name, params, env) -> PlanResult:
        product_name = params.get("target_name")
        product_id = self.item_name_to_id.get(product_name)
        if not product_id:
            return PlanResult(False, [cmd_wait(2)], f"Unknown product: {product_name}")
        
        recipe = self.product_to_recipe.get(str(product_id))
        if not recipe:
            return PlanResult(False, [cmd_wait(2)], f"No recipe found for product ID: {product_id}")
        facility_type = recipe.get("RequiredFacility", "WorkStation")
        target_facility = self.find_actor_by_type(facility_type, env)
        if not target_facility:
            return PlanResult(False, [cmd_wait(2)], f"No facility of type {facility_type} found.")
        plan = []
        for ing in recipe.get("Ingredients", []):
            ing_id = str(ing["ItemID"])
            needed_count = ing["Count"]
            
            # 检测全局库存
            total_stock = self.get_total_item_count(ing_id, env)
            
            # 【系统介入点】如果库存严重不足 (甚至不够做一次)
            if total_stock < needed_count:
                # 触发系统补货
                self._trigger_system_supply(ing_id, needed_count * 5) # 比如一次请求生产5份的量
                
                item_name = self.item_map.get(ing_id, {}).get("ItemName", ing_id)
                feedback = f"Resource Missing: {item_name}. System supply task initiated. Please Wait."
                return PlanResult(False, [cmd_wait(10)], feedback)

            # 正常规划：寻找最近的原料来源
            # 注意：这里简化逻辑，假设一次能搬完。如果背包不够，可能需要分批。
            source = self.find_actor_with_item(ing_id, needed_count, env)
            if not source:
                # 虽然总数够，但在某些不可达的地方？或者逻辑死角
                return PlanResult(False, [cmd_wait(5)], f"Could not locate {ing_id} in containers.")
            
            # 生成搬运指令
            plan.append(cmd_move(source))
            plan.append(cmd_take(ing_id, needed_count))
            plan.append(cmd_move(target_facility))
            plan.append(cmd_put(ing_id, needed_count))

        # 2. 开始制作
        plan.append(cmd_use(recipe["TaskID"]))
        
        return PlanResult(True, plan, f"Crafting {product_name} sequence started.")
    

    def _trigger_system_supply(self, item_id, amount_needed):
        """
        向黑板发布系统级补货任务
        """
        item_info = self.item_map.get(str(item_id), {})
        item_name = item_info.get("ItemName", f"Item_{item_id}")
        
        # 1. 检查重复任务
        existing_tasks = self.blackboard.get_tasks()
        task_signature = f"System Request: Supply {item_name}"
        for t in existing_tasks:
            if task_signature in t.description:
                # 任务已存在，不重复发布
                return

        # 2. 构造目标
        # Goal: Storage 里该物品数量 >= 需求量
        goal = Goal(
            target_actor="Storage", 
            property_type="Inventory",
            key=f"{item_id}.count",
            operator=">=",
            value=amount_needed
        )

        # 3. 决定任务描述和优先级
        # 简单判定：如果是作物 -> Plant；如果是制品 -> Craft
        # 这里用简单的 ID 范围判断，你可以根据实际 Item.json 修改
        is_crop = int(item_id) in [1001, 1002] 
        
        action_desc = "Plant/Harvest" if is_crop else "Produce"
        full_desc = f"{task_signature} ({action_desc})"

        new_task = BlackboardTask(
            description=full_desc,
            goal=goal,
            priority=5, # 必须高优先级，否则卡住生产线
            required_skill=None 
        )
        
        self.blackboard.post_task(new_task)
        print(f"[System] Auto-posted supply task: {full_desc}")

        