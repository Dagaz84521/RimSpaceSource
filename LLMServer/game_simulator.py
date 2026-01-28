"""
游戏世界模拟器
用于模拟指令执行后的游戏状态变化
"""
import copy


class GameSimulator:
    """游戏世界模拟器"""
    
    def __init__(self, game_state):
        """初始化模拟器"""
        self.game_state = game_state
        # 跟踪角色当前位置
        self.character_positions = {}
    
    def execute_instruction(self, character_name, instruction):
        """
        执行指令并更新游戏状态
        返回执行结果信息
        """
        if not instruction:
            return {"success": False, "message": "无效指令"}
        
        cmd = instruction.get("CommandType", "")
        
        if cmd == "Move":
            return self._execute_move(character_name, instruction)
        elif cmd == "Take":
            return self._execute_take(character_name, instruction)
        elif cmd == "Put":
            return self._execute_put(character_name, instruction)
        elif cmd == "Use":
            return self._execute_use(character_name, instruction)
        elif cmd == "Wait":
            return self._execute_wait(character_name, instruction)
        else:
            return {"success": False, "message": f"未知指令类型: {cmd}"}
    
    def _execute_move(self, character_name, instruction):
        """执行移动指令"""
        target = instruction.get("TargetName", "")
        
        # 更新角色位置
        self.character_positions[character_name] = target
        
        # 模拟消耗能量
        self._consume_energy(character_name, 0.5)
        
        return {"success": True, "message": f"{character_name} 移动到 {target}"}
    
    def _execute_take(self, character_name, instruction):
        """执行取物品指令"""
        target = instruction.get("TargetName", "")
        item_id = instruction.get("ParamID", 0)
        count = instruction.get("Count", 0)
        
        # 检查目标设施是否存在
        if target not in self.game_state["Environment"]:
            return {"success": False, "message": f"设施 {target} 不存在"}
        
        facility = self.game_state["Environment"][target]
        inventory = facility.get("Inventory", [])
        
        # 查找物品
        item_found = None
        for item in inventory:
            if item["ItemID"] == item_id:
                item_found = item
                break
        
        if not item_found:
            return {"success": False, "message": f"设施 {target} 中没有物品 {item_id}"}
        
        if item_found["Count"] < count:
            return {"success": False, "message": f"物品数量不足: 需要 {count}, 只有 {item_found['Count']}"}
        
        # 从设施中移除物品
        item_found["Count"] -= count
        if item_found["Count"] <= 0:
            inventory.remove(item_found)
        
        # 添加到角色背包
        character = self.game_state["Characters"][character_name]
        char_inventory = character.get("Inventory", [])
        
        # 查找角色背包中是否已有该物品
        char_item = None
        for item in char_inventory:
            if item["ItemID"] == item_id:
                char_item = item
                break
        
        if char_item:
            char_item["Count"] += count
        else:
            char_inventory.append({
                "ItemID": item_id,
                "ItemName": self._get_item_name(item_id),
                "Count": count
            })
        
        # 模拟消耗能量
        self._consume_energy(character_name, 0.3)
        
        return {"success": True, "message": f"{character_name} 从 {target} 取出 {count} 个物品 {item_id}"}
    
    def _execute_put(self, character_name, instruction):
        """执行放物品指令"""
        target = instruction.get("TargetName", "")
        item_id = instruction.get("ParamID", 0)
        count = instruction.get("Count", 0)
        
        # 检查角色背包
        character = self.game_state["Characters"][character_name]
        char_inventory = character.get("Inventory", [])
        
        # 查找物品
        char_item = None
        for item in char_inventory:
            if item["ItemID"] == item_id:
                char_item = item
                break
        
        if not char_item or char_item["Count"] < count:
            return {"success": False, "message": f"角色背包中没有足够的物品 {item_id}"}
        
        # 从角色背包移除
        char_item["Count"] -= count
        if char_item["Count"] <= 0:
            char_inventory.remove(char_item)
        
        # 添加到目标设施
        if target not in self.game_state["Environment"]:
            return {"success": False, "message": f"设施 {target} 不存在"}
        
        facility = self.game_state["Environment"][target]
        facility_inventory = facility.get("Inventory", [])
        
        # 查找设施中是否已有该物品
        facility_item = None
        for item in facility_inventory:
            if item["ItemID"] == item_id:
                facility_item = item
                break
        
        if facility_item:
            facility_item["Count"] += count
        else:
            facility_inventory.append({
                "ItemID": item_id,
                "ItemName": self._get_item_name(item_id),
                "Count": count
            })
        
        # 模拟消耗能量
        self._consume_energy(character_name, 0.3)
        
        return {"success": True, "message": f"{character_name} 放入 {count} 个物品 {item_id} 到 {target}"}
    
    def _execute_use(self, character_name, instruction):
        """执行使用指令"""
        target = instruction.get("TargetName", "")
        param_id = instruction.get("ParamID", 0)
        
        # 查找任务配方
        task = None
        for recipe in self.game_state.get("TaskRecipes", []):
            if recipe["ProductID"] == param_id:
                task = recipe
                break
        
        if not task:
            return {"success": False, "message": f"未找到生产物品 {param_id} 的任务"}
        
        # 检查设施中是否有足够的原料
        facility = self.game_state["Environment"].get(target)
        if not facility:
            return {"success": False, "message": f"设施 {target} 不存在"}
        
        facility_inventory = facility.get("Inventory", [])
        
        # 验证原料
        for ingredient in task.get("Ingredients", []):
            found = False
            for item in facility_inventory:
                if item["ItemID"] == ingredient["ItemID"] and item["Count"] >= ingredient["Count"]:
                    found = True
                    break
            if not found:
                return {"success": False, "message": f"设施 {target} 中原料不足"}
        
        # 一次性完成生产：消耗原料，产出物品
        # 消耗原料
        for ingredient in task.get("Ingredients", []):
            for item in facility_inventory:
                if item["ItemID"] == ingredient["ItemID"]:
                    item["Count"] -= ingredient["Count"]
                    if item["Count"] <= 0:
                        facility_inventory.remove(item)
                    break
        
        # 产出物品
        product_id = task["ProductID"]
        product_found = False
        for item in facility_inventory:
            if item["ItemID"] == product_id:
                item["Count"] += 1
                product_found = True
                break
        
        if not product_found:
            facility_inventory.append({
                "ItemID": product_id,
                "ItemName": self._get_item_name(product_id),
                "Count": 1
            })
        
        # 消耗能量（根据工作量）
        workload = task.get("TaskWorkload", 100)
        energy_cost = workload / 50.0  # 工作量越大消耗越多
        self._consume_energy(character_name, energy_cost)
        
        return {"success": True, "message": f"{character_name} 完成生产 {task['TaskName']}（工作量:{workload}）"}
    
    def _execute_wait(self, character_name, instruction):
        """执行等待指令"""
        # 等待时恢复少量能量
        character = self.game_state["Characters"][character_name]
        character["Energy"] = min(100.0, character["Energy"] + 1.0)
        
        return {"success": True, "message": f"{character_name} 等待中"}
    
    def _consume_energy(self, character_name, amount):
        """消耗角色能量"""
        character = self.game_state["Characters"][character_name]
        character["Energy"] = max(0.0, character["Energy"] - amount)
        
        # 同时增加少量饥饿度消耗
        character["Hunger"] = max(0.0, character["Hunger"] - amount * 0.1)
    
    def _get_item_name(self, item_id):
        """获取物品名称"""
        item_db = self.game_state.get("ItemDatabase", {})
        item_info = item_db.get(str(item_id), {})
        return item_info.get("ItemName", f"Item_{item_id}")
    
    def get_game_state(self):
        """获取当前游戏状态"""
        return self.game_state
    
    def print_summary(self):
        """打印游戏状态摘要"""
        print("\n=== 游戏状态摘要 ===")
        
        # 打印角色状态
        print("\n角色状态:")
        for name, char in self.game_state["Characters"].items():
            position = self.character_positions.get(name, "未知")
            inventory_count = sum(item["Count"] for item in char.get("Inventory", []))
            
            print(f"  {name}: 位置={position}, 饥饿={char['Hunger']:.1f}, 能量={char['Energy']:.1f}, 背包物品数={inventory_count}")
        
        # 打印设施库存
        print("\n设施库存:")
        for name, facility in self.game_state["Environment"].items():
            inventory = facility.get("Inventory", [])
            if inventory:
                items_str = ", ".join([f"{item['ItemName']}x{item['Count']}" for item in inventory])
                print(f"  {name}: {items_str}")
            else:
                print(f"  {name}: (空)")
