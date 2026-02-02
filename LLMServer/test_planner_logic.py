import unittest
from planner import Planner, PlanResult
from blackboard import Blackboard, BlackboardTask

# === 1. 模拟黑板 (Mock Blackboard) ===
class MockBlackboard:
    def __init__(self):
        self.tasks = []

    def post_task(self, task: BlackboardTask):
        print(f"  [Blackboard] 收到新任务: {task.description} (Goal: {task.goal.GoalDescription()})")
        self.tasks.append(task)

    def get_tasks(self):
        return self.tasks

# === 2. 可测试的 Planner (重写初始化逻辑) ===
class TestableActionPlanner(Planner):
    def __init__(self, blackboard):
        # 截断父类初始化，防止加载真实文件
        self.blackboard = blackboard
        
        # 定义 Mock 数据：Coat 需要 50 个 Cotton
        self.items = [
            {"ItemID": 1001, "ItemName": "Cotton"},
            {"ItemID": 3001, "ItemName": "Coat"}
        ]
        self.tasks = [
            {
                "TaskID": 100, 
                "ProductID": 3001, 
                "RequiredFacility": "WorkStation",
                "Ingredients": [
                    {"ItemID": 1001, "Count": 50} 
                ]
            }
        ]

        # 重建索引
        self.item_map = {str(i["ItemID"]): i for i in self.items}
        self.task_map = {str(t["TaskID"]): t for t in self.tasks}
        self.item_name_to_id = {i["ItemName"]: i["ItemID"] for i in self.items}
        self.product_to_recipe = {str(t["ProductID"]): t for t in self.tasks}
    
    # 为了防止 Planner 中有其他方法调用 game_data，我们可以模拟一个简单的 game_data 属性
    @property
    def game_data(self):
        return self

# === 3. 测试用例 ===
class TestPlannerSupplyChain(unittest.TestCase):
    
    def setUp(self):
        # 初始化黑板和 Planner
        self.blackboard = MockBlackboard()
        self.planner = TestableActionPlanner(self.blackboard)
        
        # 构造一个虚假的游戏环境 (Environment Data)
        # 场景：仓库里只有 10 个棉花，不够做大衣 (需要 50 个)
        self.mock_env = {
            "Actors": [
                {
                    "ActorName": "Storage_1",
                    "ActorType": "Storage",
                    "Inventory": {
                        "1001": {"count": 10} # 只有 10 个 Cotton
                    }
                },
                {
                    "ActorName": "WorkStation_1",
                    "ActorType": "WorkStation",
                    "Inventory": {}
                }
            ]
        }

    def test_auto_supply_chain(self):
        print("\n=== 测试开始: 资源不足触发自动补货 ===")
        
        agent_name = "Crafter_01"
        # 模拟 LLM 发出的指令：制造大衣
        params = {"target_name": "Coat"} 
        
        print(f"Agent [{agent_name}] 尝试执行: Craft Coat")
        
        # 1. 执行规划
        result = self.planner.generate_plan(agent_name, "Craft", params, self.mock_env)
        
        # === 2. 验证结果 ===
        
        # 断言 A: 计划应该标记为失败 (因为缺货)
        self.assertFalse(result.success, "Planner 应该返回失败状态")
        print("√ 验证通过: PlanResult.success 为 False")

        # 断言 B: 反馈信息里应该包含提示
        print(f"Planner 反馈信息: {result.feedback}")
        self.assertIn("System supply task initiated", result.feedback, "反馈信息应包含'系统任务已启动'")
        print("√ 验证通过: 反馈信息正确")

        # 断言 C: 动作应该是 Wait (等待补货)
        self.assertEqual(len(result.plan), 1)
        self.assertEqual(result.plan[0]["CommandType"], "Wait")
        print("√ 验证通过: 返回的动作为 Wait")

        # 断言 D: 黑板上应该多了一个任务
        tasks = self.blackboard.get_tasks()
        self.assertEqual(len(tasks), 1, "黑板上应该正好有一个新任务")
        supply_task = tasks[0]
        
        # 检查任务细节
        self.assertIn("Supply Cotton", supply_task.description)
        # Goal 数量判断：50(需求) * 5(倍率) = 250
        self.assertEqual(supply_task.goal.value, 250) 
        print("√ 验证通过: 黑板成功发布了 Supply Cotton 任务")
        
        print("=== 测试全部通过 ===")

if __name__ == "__main__":
    unittest.main()