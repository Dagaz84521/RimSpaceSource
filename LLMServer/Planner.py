"""
计划器模块 - 将LLM的高级决策分解为具体的单步指令
支持协作机制：食物请求、物品搬运协作等
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from TaskBlackboard import TaskBlackboard, TaskPriority


@dataclass
class ActionStep:
    """单步动作"""
    CommandType: str  # "Move", "Take", "Put", "Use", "Wait"
    TargetName: str = ""
    ParamID: int = 0
    Count: int = 0


class Planner:
    """
    计划器 - 将高级决策分解为具体的单步指令
    支持动态验证和重规划机制
    """
    
    def __init__(self, blackboard: TaskBlackboard):
        self.blackboard = blackboard
        self.agent_plans: Dict[str, List[ActionStep]] = {}  # 每个角色的计划队列
        self.max_plan_length = 5  # 限制计划长度，避免过长预规划
        
    def decompose_action(
        self,
        character_name: str,
        high_level_action: str,
        game_state: Dict,
        action_params: Optional[Dict] = None
    ) -> Optional[ActionStep]:
        """
        将高级决策分解为单步指令（带验证机制）
        
        Args:
            character_name: 角色名称
            high_level_action: 高级动作 (Sleep, Eat, Craft, Plant, Harvest, Transport等)
            game_state: 游戏世界状态
            action_params: 动作参数
            
        Returns:
            ActionStep: 下一个单步指令
        """
        if action_params is None:
            action_params = {}
        
        # 获取或初始化角色的计划队列
        if character_name not in self.agent_plans:
            self.agent_plans[character_name] = []
        
        # 如果还有未完成的计划，验证并返回下一步
        if self.agent_plans[character_name]:
            next_step = self.agent_plans[character_name][0]  # 先查看不pop
            
            # 验证这一步是否仍然可行
            if self._validate_step(next_step, game_state, character_name):
                # 可行，执行这一步
                return self.agent_plans[character_name].pop(0)
            else:
                # 不可行，清空计划重新规划
                print(f"[Planner] {character_name} 的计划失效，重新规划")
                self.agent_plans[character_name] = []
                # 继续下面的逻辑生成新计划
        
        # 根据高级动作生成新的计划
        plan = self._generate_plan(
            character_name,
            high_level_action,
            game_state,
            action_params
        )
        
        if plan:
            # 限制计划长度，避免过长的预规划
            if len(plan) > self.max_plan_length:
                print(f"[Planner] 计划过长({len(plan)}步)，截断为{self.max_plan_length}步")
                plan = plan[:self.max_plan_length]
            
            self.agent_plans[character_name] = plan
            return self.agent_plans[character_name].pop(0)
        
        return None
    
    def _generate_plan(
        self,
        character_name: str,
        high_level_action: str,
        game_state: Dict,
        action_params: Dict
    ) -> List[ActionStep]:
        """
        根据高级动作生成完整计划
        
        返回一系列单步指令
        """
        plan = []
        
        if high_level_action == "Sleep":
            plan = self._plan_sleep(character_name, game_state)
            
        elif high_level_action == "Eat":
            plan = self._plan_eat(character_name, game_state)
            
        elif high_level_action == "Craft":
            recipe_id = action_params.get("recipe_id", 0)
            plan = self._plan_craft(character_name, game_state, recipe_id)
            
        elif high_level_action == "Plant":
            plant_id = action_params.get("plant_id", 0)
            plan = self._plan_plant(character_name, game_state, plant_id)
            
        elif high_level_action == "Harvest":
            target_name = action_params.get("target_name", "")
            plan = self._plan_harvest(character_name, game_state, target_name)
            
        elif high_level_action == "Transport":
            # 搬运物品
            plan = self._plan_transport(character_name, game_state, action_params)
            
        elif high_level_action == "CheckBlackboard":
            # 检查黑板任务
            plan = self._plan_check_blackboard(character_name, game_state)
            
        else:
            print(f"[Planner] 未知的高级动作: {high_level_action}")
        
        return plan
    
    def _plan_sleep(self, character_name: str, game_state: Dict) -> List[ActionStep]:
        """规划睡觉"""
        plan = []
        
        # 1. 找到最近的床
        bed_name = self._find_nearest_facility(game_state, "Bed")
        if not bed_name:
            print(f"[Planner] {character_name} 找不到床")
            return []
        
        # 2. 移动到床
        plan.append(ActionStep(CommandType="Move", TargetName=bed_name))
        
        # 3. 使用床（睡觉）
        plan.append(ActionStep(CommandType="Use", TargetName=bed_name))
        
        return plan
    
    def _plan_eat(self, character_name: str, game_state: Dict) -> List[ActionStep]:
        """
        规划吃饭
        如果没有食物，发布到黑板请求厨师制作
        """
        plan = []
        
        # 1. 检查自己背包是否有食物
        character_info = self._get_character_info(game_state, character_name)
        if not character_info:
            return []
        
        inventory = character_info.get("Inventory", [])
        food_item = self._find_food_in_inventory(inventory)
        
        if food_item:
            # 有食物，直接吃
            plan.append(ActionStep(
                CommandType="Use",
                ParamID=food_item["ItemID"],
                Count=1
            ))
            return plan
        
        # 2. 检查仓库是否有食物
        storage_name, food_in_storage = self._find_food_in_storage(game_state)
        
        if food_in_storage:
            # 仓库有食物，去取
            plan.append(ActionStep(CommandType="Move", TargetName=storage_name))
            plan.append(ActionStep(
                CommandType="Take",
                TargetName=storage_name,
                ParamID=food_in_storage["ItemID"],
                Count=1
            ))
            plan.append(ActionStep(
                CommandType="Use",
                ParamID=food_in_storage["ItemID"],
                Count=1
            ))
            return plan
        
        # 3. 没有食物，发布任务到黑板请求厨师制作
        print(f"[Planner] {character_name} 没有食物，发布烹饪任务到黑板")
        self.blackboard.publish_task(
            publisher=character_name,
            task_type="Cook",
            description=f"请求制作食物（饥饿度高）",
            priority=TaskPriority.HIGH,
            item_id=None,  # 任何食物
            item_count=1
        )
        
        # 等待一段时间
        plan.append(ActionStep(CommandType="Wait"))
        
        return plan
    
    def _plan_craft(
        self,
        character_name: str,
        game_state: Dict,
        recipe_id: int
    ) -> List[ActionStep]:
        """
        规划制作物品
        检查原料，如果缺少则发布搬运任务
        """
        plan = []
        
        # 1. 获取配方信息
        recipe = self._get_recipe(game_state, recipe_id)
        if not recipe:
            print(f"[Planner] 找不到配方 {recipe_id}")
            return []
        
        # 2. 找到对应的工作台
        facility_type = recipe.get("RequiredFacility", "")
        facility_name = self._find_nearest_facility(game_state, facility_type)
        if not facility_name:
            print(f"[Planner] 找不到 {facility_type}")
            return []
        
        # 3. 检查工作台是否有足够的原料
        ingredients = recipe.get("Ingredients", [])
        facility_inventory = self._get_facility_inventory(game_state, facility_name)
        
        missing_items = self._check_missing_ingredients(ingredients, facility_inventory)
        
        if missing_items:
            # 4. 检查仓库是否有缺失的原料
            storage_has_items = self._check_storage_for_items(game_state, missing_items)
            
            if storage_has_items:
                # 协作策略：发布部分搬运任务，自己也搬运一部分
                self._publish_transport_tasks(
                    character_name,
                    missing_items,
                    storage_has_items,
                    facility_name
                )
                
                # 自己先搬运一部分（例如一半）
                self_transport_items = missing_items[:len(missing_items)//2] if len(missing_items) > 1 else missing_items
                plan.extend(self._generate_transport_steps(
                    game_state,
                    self_transport_items,
                    facility_name
                ))
        
        # 5. 移动到工作台并执行制作
        plan.append(ActionStep(CommandType="Move", TargetName=facility_name))
        plan.append(ActionStep(
            CommandType="Use",
            TargetName=facility_name,
            ParamID=recipe_id
        ))
        
        return plan
    
    def _plan_transport(
        self,
        character_name: str,
        game_state: Dict,
        params: Dict
    ) -> List[ActionStep]:
        """规划搬运物品"""
        plan = []
        
        item_id = params.get("item_id", 0)
        count = params.get("count", 1)
        from_location = params.get("from_location", "")
        to_location = params.get("to_location", "")
        
        # 1. 移动到源位置
        plan.append(ActionStep(CommandType="Move", TargetName=from_location))
        
        # 2. 取出物品
        plan.append(ActionStep(
            CommandType="Take",
            TargetName=from_location,
            ParamID=item_id,
            Count=count
        ))
        
        # 3. 移动到目标位置
        plan.append(ActionStep(CommandType="Move", TargetName=to_location))
        
        # 4. 放入物品
        plan.append(ActionStep(
            CommandType="Put",
            TargetName=to_location,
            ParamID=item_id,
            Count=count
        ))
        
        return plan
    
    def _plan_check_blackboard(
        self,
        character_name: str,
        game_state: Dict
    ) -> List[ActionStep]:
        """
        检查黑板任务并认领
        """
        # 获取可用任务
        available_tasks = self.blackboard.get_available_tasks(character_name)
        
        if not available_tasks:
            # 没有任务，等待
            return [ActionStep(CommandType="Wait")]
        
        # 认领第一个高优先级任务
        task = available_tasks[0]
        self.blackboard.claim_task(task.task_id, character_name)
        self.blackboard.start_task(task.task_id)
        
        # 根据任务类型生成计划
        if task.task_type == "Transport":
            return self._plan_transport(character_name, game_state, {
                "item_id": task.item_id,
                "count": task.item_count,
                "from_location": task.metadata.get("from_location", ""),
                "to_location": task.target_location
            })
        
        elif task.task_type == "Cook":
            # 烹饪任务
            return self._plan_craft(character_name, game_state, task.recipe_id or 1)
        
        return [ActionStep(CommandType="Wait")]
    
    def _plan_plant(self, character_name: str, game_state: Dict, plant_id: int) -> List[ActionStep]:
        """规划种植"""
        plan = []
        facility_name = self._find_nearest_facility(game_state, "CultivateChamber")
        if facility_name:
            plan.append(ActionStep(CommandType="Move", TargetName=facility_name))
            plan.append(ActionStep(
                CommandType="Use",
                TargetName=facility_name,
                ParamID=plant_id
            ))
        return plan
    
    def _plan_harvest(self, character_name: str, game_state: Dict, target_name: str) -> List[ActionStep]:
        """规划收获"""
        plan = []
        plan.append(ActionStep(CommandType="Move", TargetName=target_name))
        plan.append(ActionStep(CommandType="Use", TargetName=target_name))
        return plan
    
    # ========== 辅助方法 ==========
    
    def _validate_step(
        self,
        step: ActionStep,
        game_state: Dict,
        character_name: str
    ) -> bool:
        """
        验证单步指令是否仍然可行
        这是关键的动态验证机制
        """
        command_type = step.CommandType
        
        # Wait指令总是有效
        if command_type == "Wait":
            return True
        
        # Move指令：检查目标是否存在
        if command_type == "Move":
            target_name = step.TargetName
            if not target_name:
                return False
            
            environment = game_state.get("Environment", {})
            if target_name not in environment:
                print(f"[验证失败] {target_name} 不存在")
                return False
            return True
        
        # Take指令：检查源位置是否有足够的物品
        if command_type == "Take":
            target_name = step.TargetName
            item_id = step.ParamID
            count = step.Count
            
            environment = game_state.get("Environment", {})
            if target_name not in environment:
                print(f"[验证失败] Take目标 {target_name} 不存在")
                return False
            
            inventory = environment[target_name].get("Inventory", [])
            for item in inventory:
                if item.get("ItemID") == item_id:
                    if item.get("Count", 0) >= count:
                        return True
                    else:
                        print(f"[验证失败] {target_name} 中物品{item_id}数量不足")
                        return False
            
            print(f"[验证失败] {target_name} 中没有物品{item_id}")
            return False
        
        # Put指令：检查角色是否有该物品
        if command_type == "Put":
            item_id = step.ParamID
            count = step.Count
            
            character_info = self._get_character_info(game_state, character_name)
            if not character_info:
                return False
            
            inventory = character_info.get("Inventory", [])
            for item in inventory:
                if item.get("ItemID") == item_id:
                    if item.get("Count", 0) >= count:
                        return True
                    else:
                        print(f"[验证失败] {character_name} 背包中物品{item_id}数量不足")
                        return False
            
            print(f"[验证失败] {character_name} 背包中没有物品{item_id}")
            return False
        
        # Use指令：检查目标是否存在且可用
        if command_type == "Use":
            target_name = step.TargetName
            if target_name:
                environment = game_state.get("Environment", {})
                if target_name not in environment:
                    print(f"[验证失败] Use目标 {target_name} 不存在")
                    return False
                
                # TODO: 可以进一步检查设施是否被占用
            
            return True
        
        # 未知指令类型，保守处理返回True
        return True
    
    def clear_plan(self, character_name: str):
        """清空角色的计划队列（用于紧急情况）"""
        if character_name in self.agent_plans:
            self.agent_plans[character_name] = []
            print(f"[Planner] 清空 {character_name} 的计划队列")
    
    def get_remaining_steps(self, character_name: str) -> int:
        """获取角色剩余的计划步骤数"""
        return len(self.agent_plans.get(character_name, []))
    
    # ========== 原有辅助方法 ==========
    
    def _find_nearest_facility(self, game_state: Dict, facility_type: str) -> Optional[str]:
        """查找最近的设施"""
        actors = game_state.get("Environment", {})
        for actor_name, actor_data in actors.items():
            if actor_data.get("Type") == facility_type:
                return actor_name
        return None
    
    def _get_character_info(self, game_state: Dict, character_name: str) -> Optional[Dict]:
        """获取角色信息"""
        characters = game_state.get("Characters", {})
        return characters.get(character_name)
    
    def _find_food_in_inventory(self, inventory: List[Dict]) -> Optional[Dict]:
        """在背包中查找食物"""
        for item in inventory:
            # 假设食物的ItemID范围是某个特定区间，或者有Type字段
            # 这里简化处理
            if item.get("ItemID") in [1, 2, 3]:  # 示例：食物ID
                return item
        return None
    
    def _find_food_in_storage(self, game_state: Dict) -> Tuple[Optional[str], Optional[Dict]]:
        """在仓库中查找食物"""
        actors = game_state.get("Environment", {})
        for actor_name, actor_data in actors.items():
            if actor_data.get("Type") == "Storage":
                inventory = actor_data.get("Inventory", [])
                food = self._find_food_in_inventory(inventory)
                if food:
                    return actor_name, food
        return None, None
    
    def _get_recipe(self, game_state: Dict, recipe_id: int) -> Optional[Dict]:
        """获取配方信息"""
        recipes = game_state.get("TaskRecipes", [])
        for recipe in recipes:
            if recipe.get("TaskID") == recipe_id:
                return recipe
        return None
    
    def _get_facility_inventory(self, game_state: Dict, facility_name: str) -> List[Dict]:
        """获取设施的库存"""
        actors = game_state.get("Environment", {})
        facility = actors.get(facility_name, {})
        return facility.get("Inventory", [])
    
    def _check_missing_ingredients(
        self,
        required: List[Dict],
        current: List[Dict]
    ) -> List[Dict]:
        """检查缺失的原料"""
        missing = []
        for req_item in required:
            req_id = req_item.get("ItemID")
            req_count = req_item.get("Count", 1)
            
            # 查找当前库存
            current_count = 0
            for curr_item in current:
                if curr_item.get("ItemID") == req_id:
                    current_count = curr_item.get("Count", 0)
                    break
            
            if current_count < req_count:
                missing.append({
                    "ItemID": req_id,
                    "Count": req_count - current_count
                })
        
        return missing
    
    def _check_storage_for_items(
        self,
        game_state: Dict,
        items: List[Dict]
    ) -> Dict[int, int]:
        """检查仓库中是否有指定物品"""
        storage_items = {}
        actors = game_state.get("Environment", {})
        
        for actor_name, actor_data in actors.items():
            if actor_data.get("Type") == "Storage":
                inventory = actor_data.get("Inventory", [])
                for item in inventory:
                    item_id = item.get("ItemID")
                    count = item.get("Count", 0)
                    storage_items[item_id] = storage_items.get(item_id, 0) + count
        
        return storage_items
    
    def _publish_transport_tasks(
        self,
        publisher: str,
        missing_items: List[Dict],
        storage_items: Dict[int, int],
        target_location: str
    ):
        """发布搬运任务到黑板"""
        # 发布一半的搬运任务（另一半自己做）
        tasks_to_publish = missing_items[len(missing_items)//2:] if len(missing_items) > 1 else []
        
        for item in tasks_to_publish:
            item_id = item.get("ItemID")
            count = item.get("Count", 1)
            
            if item_id in storage_items and storage_items[item_id] >= count:
                self.blackboard.publish_task(
                    publisher=publisher,
                    task_type="Transport",
                    description=f"搬运物品 {item_id} x{count} 到 {target_location}",
                    priority=TaskPriority.NORMAL,
                    item_id=item_id,
                    item_count=count,
                    target_location=target_location,
                    metadata={"from_location": "Storage"}
                )
    
    def _generate_transport_steps(
        self,
        game_state: Dict,
        items: List[Dict],
        target_location: str
    ) -> List[ActionStep]:
        """生成搬运步骤"""
        steps = []
        
        # 找到仓库
        storage_name = self._find_nearest_facility(game_state, "Storage")
        if not storage_name:
            return []
        
        for item in items:
            item_id = item.get("ItemID")
            count = item.get("Count", 1)
            
            # 移动到仓库
            steps.append(ActionStep(CommandType="Move", TargetName=storage_name))
            # 取出物品
            steps.append(ActionStep(
                CommandType="Take",
                TargetName=storage_name,
                ParamID=item_id,
                Count=count
            ))
            # 移动到目标位置
            steps.append(ActionStep(CommandType="Move", TargetName=target_location))
            # 放入物品
            steps.append(ActionStep(
                CommandType="Put",
                TargetName=target_location,
                ParamID=item_id,
                Count=count
            ))
        
        return steps
