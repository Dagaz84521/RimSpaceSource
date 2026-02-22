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
        target_count = params.get("count", 1)
        # print(f"[Planner] Crafting request: {product_name} x{target_count} (ID: {product_id})")
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
            needed_count = ing["Count"] * target_count
            
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
    

    def _trigger_system_supply(self, item_id, amount_needed, target_facility_name="WorkStation", environment=None):
        """
        向黑板发布系统级补货任务
        【修改】：移除了 parent_task_id 参数和所有的依赖强绑定逻辑
        """
        if environment is None:
            return None
            
        item_info = self.item_map.get(str(item_id), {})
        item_name = item_info.get("ItemName", f"Item_{item_id}")
        
        # print(f"[_trigger_system_supply] 检查补货需求: {item_name} (ID:{item_id}) x{amount_needed} -> {target_facility_name}")
        
        existing_tasks = self.blackboard.tasks
        task_signature_produce = f"System Request: Produce {item_name}"
        task_signature_transport = f"System Request: Transport {item_name}"
        
        # 1. 防止重复派发
        for t in existing_tasks:
            if task_signature_produce in t.description or task_signature_transport in t.description:
                # print(f"[_trigger_system_supply] 任务已存在，跳过: {t.description}")
                return t.task_id 

        # 2. 检查设施库存
        target_stock = self.get_actor_item_count(target_facility_name, item_id, environment)
        # print(f"[_trigger_system_supply] 设施库存: {target_stock}/{amount_needed}")
        if target_stock >= amount_needed:
            # print(f"[_trigger_system_supply] 设施库存充足，无需补货")
            return None

        # 3. 检查全局库存
        total_stock = self.get_total_item_count(item_id, environment)
        # print(f"[_trigger_system_supply] 全局库存: {total_stock}/{amount_needed}")
        new_task = None

        if total_stock < amount_needed:
            # === 分支 A: 生产任务 ===
            # print(f"[_trigger_system_supply] 全局库存不足，创建生产任务")
            recipe = self.product_to_recipe.get(str(item_id))
            skill_name = next(iter(recipe.get("RequiredSkill", {}))) if recipe and recipe.get("RequiredSkill") else None
            full_desc = f"{task_signature_produce} (For {target_facility_name})"
            
            # 生产的目标是：全局库存足够
            goal_produce = Goal(
                target_actor="Global",
                property_type="Inventory",
                key=str(item_id),
                operator=">=",
                value=amount_needed
            )

            # 生产的先决条件是：生产材料在生产地点中足够
            preconditions = []
            if recipe:
                ingredients = recipe.get("Ingredients", [])
                for ing in ingredients:
                    ing_id = str(ing["ItemID"])
                    ing_count = ing["Count"] * amount_needed
                    
                    # 注入状态条件
                    preconditions.append(Goal(
                        target_actor="Global",
                        property_type="Inventory", 
                        key=ing_id, 
                        operator=">=", 
                        value=ing_count
                    ))
                    
                    # 顺便递归派发一下原材料的生产/搬运任务
                    ing_stock = self.get_total_item_count(ing_id, environment)
                    if ing_stock < ing_count:
                        ingredient_target = self.product_to_recipe.get(ing_id, {}).get("RequiredFacility", "WorkStation")
                        # print(f"[_trigger_system_supply] 递归补货原材料: {ing_id} x{ing_count}")
                        self._trigger_system_supply(ing_id, ing_count, ingredient_target, environment)

            new_task = BlackboardTask(
                description=full_desc,
                goal=goal_produce,
                priority=6,
                required_skill=skill_name,
                preconditions=preconditions
            )
            # print(f"[_trigger_system_supply] 创建生产任务: {full_desc}")
        else:
            # === 分支 B: 搬运任务 ===
            # print(f"[_trigger_system_supply] 全局库存充足，创建搬运任务")
            full_desc = f"{task_signature_transport} (From Storage to {target_facility_name})"
            
            # 搬运的目标是：指定设施库存足够
            goal_transport = Goal(
                target_actor=target_facility_name,
                property_type="Inventory",
                key=str(item_id),
                operator=">=",
                value=amount_needed
            )
            
            new_task = BlackboardTask(
                description=full_desc,
                goal=goal_transport,
                priority=5,
                required_skill=None,  # 任何人都能搬
                preconditions=[]      # 搬运任务无条件，随时可干 (因为货已经存在了)
            )
            
            new_task.item_id = item_id
            new_task.source = "Storage"
            new_task.destination = target_facility_name
            new_task.count = amount_needed
            # print(f"[_trigger_system_supply] 创建搬运任务: {full_desc}")
            
        if new_task:
            self.blackboard.post_task(new_task)
            # print(f"[_trigger_system_supply] 任务已发布到黑板: {new_task.task_id}")
        return new_task.task_id if new_task else None

    # === planner.py ===

    def analyze_and_post_crafting_task(self, facility_name, task_id, count, environment):
        """
        Planner 统一解析制造需求：生成主任务，并一口气铺开整个供应链
        """
        # 1. 明确最终目标 (Goal)
        goal_craft = Goal(
            target_actor=facility_name,
            property_type="TaskList",
            key=str(task_id),
            operator="<=",
            value=0
        )
        
        # 2. 查阅配方，构建先决条件
        preconditions = []
        recipe = self.product_to_recipe.get(str(task_id))
        
        if recipe:
            for ing in recipe.get("Ingredients", []):
                ing_id = str(ing["ItemID"])
                ing_count = ing["Count"] * count
                
                # 制造的先决条件：当前设施里必须有足够的原料
                cond_ws_has_item = Goal(
                    target_actor=facility_name,
                    property_type="Inventory",
                    key=ing_id,
                    operator=">=",
                    value=ing_count
                )
                preconditions.append(cond_ws_has_item)
                
                # 【核心】：直接递归铺开该原料的供应链（搬运 + 生产）
                self._build_supply_chain(ing_id, ing_count, facility_name, environment)
                
        # 3. 创建并发布主任务
        item_name = self.item_map.get(str(task_id), {}).get("ItemName", f"Item_{task_id}")
        task_desc = f"Make {count}× {item_name} at {facility_name}"
        
        task_craft = BlackboardTask(
            description=task_desc,
            goal=goal_craft,
            required_skill="canCraft",
            preconditions=preconditions
        )
        self.blackboard.post_task(task_craft)


    def _build_supply_chain(self, item_id, amount_needed, target_facility, environment):
        """
        全自动声明式供应链：同时发布搬运和生产任务，由系统状态自动解锁
        """
        item_name = self.item_map.get(str(item_id), {}).get("ItemName", f"Item_{item_id}")
        
        # 包装环境数据以符合 Goal.is_satisfied 的期望格式
        wrapped_env = {"Environment": environment} if "Environment" not in environment else environment
        
        # 定义核心状态判定
        goal_facility_has_item = Goal(target_actor=target_facility, property_type="Inventory", key=str(item_id), operator=">=", value=amount_needed)
        cond_global_has_item = Goal(target_actor="Global", property_type="Inventory", key=str(item_id), operator=">=", value=amount_needed)
        
        # ==========================================
        # 任务 1：搬运任务 (解决物资在别处的问题)
        # ==========================================
        # 如果设施里还没货，就把搬运任务挂上去
        if not goal_facility_has_item.is_satisfied(wrapped_env):
            task_transport = BlackboardTask(
                description=f"System Request: Transport {item_name} (To {target_facility})",
                goal=goal_facility_has_item, # 搬运的终点是设施有货
                priority=5,
                required_skill=None,  # 任何人都能搬
                preconditions=[cond_global_has_item] # 【关键】：前提是全局有货
            )
            # 附加元数据给动作执行层
            task_transport.item_id = item_id
            task_transport.source = "Storage"
            task_transport.destination = target_facility
            task_transport.count = amount_needed
            self.blackboard.post_task(task_transport)
            
        # ==========================================
        # 任务 2：生产任务 (解决全地图都没货的问题)
        # ==========================================
        # 如果连全局都没货，就把生产任务也挂上去
        if not cond_global_has_item.is_satisfied(wrapped_env):
            recipe = self.product_to_recipe.get(str(item_id))
            skill_name = None
            produce_preconds = []
            
            if recipe:
                skill_name = next(iter(recipe.get("RequiredSkill", {}))) if recipe.get("RequiredSkill") else None
                produce_facility = recipe.get("RequiredFacility", "WorkStation")
                
                # 递归处理二级原料（例如做衣服需要布，做布还需要种棉花）
                for sub_ing in recipe.get("Ingredients", []):
                    sub_id = str(sub_ing["ItemID"])
                    sub_count = sub_ing["Count"] * amount_needed
                    
                    # 生产的前提：全局必须有二级原料
                    produce_preconds.append(
                        Goal(target_actor="Global", property_type="Inventory", key=sub_id, operator=">=", value=sub_count)
                    )
                    # 递归铺展二级原料的搬运和生产
                    self._build_supply_chain(sub_id, sub_count, produce_facility, environment)
                    
            task_produce = BlackboardTask(
                description=f"System Request: Produce {item_name}",
                goal=cond_global_has_item, # 生产的终点是全局有货
                priority=6,
                required_skill=skill_name,
                preconditions=produce_preconds
            )
            self.blackboard.post_task(task_produce)