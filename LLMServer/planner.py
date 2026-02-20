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
                item_count = inv.get(str_id, 0)
                if isinstance(item_count, int):
                    total += item_count
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
                    count = inv.get(str_id, 0)
                    if isinstance(count, int) and count >= min_count:
                        return actor.get("ActorName")
        
        # 其次查找任意容器
        for actor in actors:
            inv = actor.get("Inventory", {})
            if isinstance(inv, dict):
                count = inv.get(str_id, 0)
                if isinstance(count, int) and count >= min_count:
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

    def get_actor_item_count(self, actor_name, item_id, environment) -> int:
        """获取指定设施/容器中某物品的数量"""
        if not actor_name:
            return 0
        str_id = str(item_id)
        for actor in environment.get("Actors", []):
            if actor.get("ActorName") != actor_name:
                continue
            inv = actor.get("Inventory", {})
            if isinstance(inv, dict):
                count = inv.get(str_id, 0)
                return count if isinstance(count, int) else 0
        return 0
    
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
        current_loc = params.get("current_location")
        source = self.find_actor_with_item(food_id, 1, env)
        if not source:
            # 游戏中没有食物，触发系统任务
            # 补充3个食物，根据游戏内设定，刚好满足殖民地所有人的进餐需求
            self._trigger_system_supply(food_id, 3, "Stove", env)
            return PlanResult(False, [cmd_wait(5)], "No food available. Cooking task posted.")
        plan = []
        if source and current_loc != source:
            plan.append(cmd_move(source))
            current_loc = source
        plan.append(cmd_take(food_id, 1))
        table = self.find_actor_by_type("Table", env)
        if table:
            if current_loc != table:
                plan.append(cmd_move(table))
                current_loc = table
        plan.append(cmd_use(food_id))
        return PlanResult(True, plan, "Eating sequence")
    
    def _plan_plant(self, agent_name, params, env) -> PlanResult:
        target = params.get("target_name")
        if not target:
            return PlanResult(False, [cmd_wait(2)], "No target specified for planting.")
        current_loc = params.get("current_location")
        plan = []
        if current_loc != target:
            plan.append(cmd_move(target))
        plan.append(cmd_use(0))
        return PlanResult(True, plan, "Planting sequence")
    
    def _plan_harvest(self, agent_name, params, env) -> PlanResult:
        target = params.get("target_name")
        if not target:
            return PlanResult(False, [cmd_wait(2)], "No target specified for harvesting.")
        current_loc = params.get("current_location")
        plan = []
        if current_loc != target:
            plan.append(cmd_move(target))
        plan.append(cmd_use(0))
        return PlanResult(True, plan, "Harvesting sequence")
    
    def _plan_transport(self, agent_name, params, env) -> PlanResult:
        source = params.get("target_name")
        destination = params.get("aux_name")
        item_id = params.get("item_id")
        count = params.get("count", 1)
        if not source or not destination or not item_id:
            return PlanResult(False, [cmd_wait(2)], "Incomplete parameters for transport.")
        current_loc = params.get("current_location")
        plan = []
        if current_loc != source:
            plan.append(cmd_move(source))
            current_loc = source
        plan.append(cmd_take(item_id, count))
        if destination != current_loc:
            plan.append(cmd_move(destination))
            current_loc = destination
        plan.append(cmd_put(item_id, count))
        return PlanResult(True, plan, f"Transporting {count} items.")
    
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
        missing_resources = []  # 收集所有缺失的原料
        current_loc = params.get("current_location")
        
        for ing in recipe.get("Ingredients", []):
            ing_id = str(ing["ItemID"])
            needed_count = ing["Count"]
            
            # 检测全局库存
            total_stock = self.get_total_item_count(ing_id, env)
            
            # 【系统介入点】如果库存不足
            if total_stock < needed_count:
                # 记录缺失原料但不立即返回
                missing_resources.append((ing_id, needed_count, self.item_map.get(ing_id, {}).get("ItemName", ing_id)))
                # 触发系统补货
                self._trigger_system_supply(ing_id, needed_count, target_facility, env)
            else:
                # 库存充足，生成搬运指令
                source = self.find_actor_with_item(ing_id, needed_count, env)
                if not source:
                    # 虽然总数够，但在某些不可达的地方？或者逻辑死角
                    return PlanResult(False, [cmd_wait(5)], f"Could not locate {ing_id} in containers.")
                
                # 生成搬运指令
                if source != target_facility:
                    if current_loc != source:
                        plan.append(cmd_move(source))
                        current_loc = source
                    plan.append(cmd_take(ing_id, needed_count))
                    if current_loc != target_facility:
                        plan.append(cmd_move(target_facility))
                        current_loc = target_facility
                    plan.append(cmd_put(ing_id, needed_count))

        # 如果有任何缺失的原料，返回失败并等待
        if missing_resources:
            resource_names = ", ".join([name for _, _, name in missing_resources])
            feedback = f"Resources Missing: {resource_names}. System supply tasks initiated. Please Wait."
            return PlanResult(False, [cmd_wait(10)], feedback)

        # 2. 开始制作
        if current_loc != target_facility:
            plan.append(cmd_move(target_facility))
            current_loc = target_facility
        plan.append(cmd_use(recipe["TaskID"]))
        
        return PlanResult(True, plan, f"Crafting {product_name} sequence started.")
    

    def _trigger_system_supply(self, item_id, amount_needed, target_facility_name="WorkStation", environment=None, parent_task_id=None):
        """
        向黑板发布系统级补货任务 (智能分流版)
        支持递归检查生产链依赖
        :param parent_task_id: 父任务ID，新任务将成为父任务的依赖项
        :return: 新创建任务的task_id（如果创建），None（如果未创建）
        """
        if environment is None:
            print("[System] Warning: environment is None in _trigger_system_supply")
            return None
            
        item_info = self.item_map.get(str(item_id), {})
        item_name = item_info.get("ItemName", f"Item_{item_id}")
        
        # 1. 检查重复任务 (避免重复发布)
        existing_tasks = self.blackboard.tasks  # 直接访问 tasks 列表
        task_signature_produce = f"System Request: Produce {item_name}"
        task_signature_transport = f"System Request: Transport {item_name}"
        
        for t in existing_tasks:
            if task_signature_produce in t.description or task_signature_transport in t.description:
                # 任务已存在，如果有父任务，将现有任务加入父任务的依赖
                if parent_task_id:
                    parent_task = next((pt for pt in existing_tasks if pt.task_id == parent_task_id), None)
                    if parent_task and t.task_id not in parent_task.dependencies:
                        parent_task.dependencies.append(t.task_id)
                        print(f"[System] Added existing task {t.description} as dependency of parent task")
                return t.task_id

        # 2. 获取目标设施库存，已满足则无需发布任务
        target_stock = self.get_actor_item_count(target_facility_name, item_id, environment)
        if target_stock >= amount_needed:
            return None

        # 3. 获取全局库存 (Storage + 所有容器)
        total_stock = self.get_total_item_count(item_id, environment)
        
        # 4. 构造 Goal (无论生产还是搬运，最终目的都是让目标设施里有东西)
        goal = Goal(
            target_actor=target_facility_name,  # 直接指向目标设施
            property_type="Inventory",
            key=str(item_id),
            operator=">=",
            value=amount_needed
        )

        new_task = None
        dependency_task_ids = []  # 收集当前任务依赖的子任务ID

        # 5. 核心分流逻辑
        if total_stock < amount_needed:
            # === 分支 A: 生产任务 (Production) ===
            # 只有当全局缺货时，才发布生产任务
            
            # 查找配方以确定所需技能
            recipe = self.product_to_recipe.get(str(item_id))
            print(f"[Debug] Looking for recipe of item {item_id}: {'Found' if recipe else 'NOT FOUND'}")
            
            if recipe:
                required_skill_dict = recipe.get("RequiredSkill", {})
                # 提取技能名 (例如 "CanCraft")
                skill_name = next(iter(required_skill_dict)) if required_skill_dict else None
                
                # 【递归检查】：检查生产该物品所需的所有原料
                ingredients = recipe.get("Ingredients", [])
                print(f"[Debug] Item {item_id} has {len(ingredients)} ingredients")
                
                # 先创建当前生产任务（占位，稍后补充依赖）
                full_desc = f"{task_signature_produce} (For {target_facility_name})"
                new_task = BlackboardTask(
                    description=full_desc,
                    goal=goal,
                    priority=6,
                    required_skill=skill_name,
                    dependencies=[]  # 稍后填充
                )
                
                # 递归处理所有原料，收集依赖任务ID
                for ing in ingredients:
                    ing_id = str(ing["ItemID"])
                    ing_count = ing["Count"]
                    ing_stock = self.get_total_item_count(ing_id, environment)
                    
                    print(f"[Debug] Ingredient {ing_id}: need={ing_count}, stock={ing_stock}")
                    
                    # 如果原料不足，递归触发原料的生产/搬运任务
                    if ing_stock < ing_count:
                        # 获取原料的配方以确定其生产设施
                        ingredient_recipe = self.product_to_recipe.get(ing_id)
                        ingredient_target = ingredient_recipe.get("RequiredFacility", "WorkStation") if ingredient_recipe else "WorkStation"
                        
                        ing_name = self.item_map.get(ing_id, {}).get("ItemName", f"Item_{ing_id}")
                        print(f"[System] Recursively triggered supply for ingredient: {ing_name} -> {ingredient_target}")
                        
                        # 递归调用，传入当前任务ID作为父任务
                        child_task_id = self._trigger_system_supply(ing_id, ing_count, ingredient_target, environment, new_task.task_id)
                        if child_task_id and child_task_id not in dependency_task_ids:
                            dependency_task_ids.append(child_task_id)
                    else:
                        print(f"[Debug] Ingredient {ing_id} is sufficiently stocked.")
                        # 直接触发搬运任务确保原料到位
                        child_task_id = self._trigger_system_supply(ing_id, ing_count, target_facility_name, environment, new_task.task_id)
                        if child_task_id and child_task_id not in dependency_task_ids:
                            dependency_task_ids.append(child_task_id)
                
                # 将收集到的依赖任务ID赋值给新任务
                new_task.dependencies = dependency_task_ids
                print(f"[System] Auto-posted PRODUCTION task: {full_desc} [Req: {skill_name}] [Deps: {len(dependency_task_ids)}]")
            else:
                skill_name = None
                full_desc = f"{task_signature_produce} (For {target_facility_name})"
                new_task = BlackboardTask(
                    description=full_desc,
                    goal=goal,
                    priority=6,
                    required_skill=skill_name,
                    dependencies=[]
                )
                print(f"[System] Auto-posted PRODUCTION task (no recipe): {full_desc}")
            
        else:
            # === 分支 B: 搬运任务 (Logistics) ===
            # 货是够的，只是没到位
            full_desc = f"{task_signature_transport} (From Storage to {target_facility_name})"
            
            new_task = BlackboardTask(
                description=full_desc,
                goal=goal,
                priority=5,
                required_skill=None,  # <--- 【关键】: 不限技能，Chef 可以帮忙搬运
                dependencies=[]  # 搬运任务通常无依赖
            )
            
            # 【新增】为搬运任务添加元数据，以便 agent_manager 正确调用 _plan_transport
            new_task.item_id = item_id
            new_task.source = "Storage"
            new_task.destination = target_facility_name
            new_task.count = amount_needed
            
            print(f"[System] Auto-posted TRANSPORT task: {full_desc}")
        
        # 发布任务到黑板
        self.blackboard.post_task(new_task)
        
        # 如果有父任务，将当前任务添加到父任务的依赖列表
        if parent_task_id and new_task:
            parent_task = next((t for t in self.blackboard.tasks if t.task_id == parent_task_id), None)
            if parent_task and new_task.task_id not in parent_task.dependencies:
                parent_task.dependencies.append(new_task.task_id)
                print(f"[System] Linked {new_task.description} as dependency of parent task")
        
        return new_task.task_id if new_task else None

        