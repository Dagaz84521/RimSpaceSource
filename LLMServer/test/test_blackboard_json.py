import unittest
import json
import os
from blackboard import Goal

class TestGoalIsSatisfiedWithJson(unittest.TestCase):
    def setUp(self):
        # 这里可以通过环境变量或参数指定json路径，默认用Farmer_Begining.json
        test_json = os.environ.get("GOAL_TEST_JSON", "test/TestJson/Farmer_Begining.json")
        with open(test_json, "r", encoding="utf-8") as f:
            self.game_state = json.load(f)

    def test_cultivate_phase(self):
        goal = Goal("CultivateChamber_1", "CultivateInfo", "CurrentPhase", "==", "ECultivatePhase::ECP_WaitingToPlant")
        self.assertTrue(goal.is_satisfied(self.game_state))

    def test_storage_cotton_count(self):
        goal = Goal("Storage", "Inventory", "1001", "==", {"count": 10, "name": "棉花"})
        self.assertTrue(goal.is_satisfied(self.game_state))

    def test_workstation_task(self):
        goal = Goal("WorkStation", "TaskList", "2001", ">=", 10)
        self.assertTrue(goal.is_satisfied(self.game_state))

if __name__ == "__main__":
    unittest.main()
