import unittest
from blackboard import Goal

class TestGoalIsSatisfied(unittest.TestCase):
    def setUp(self):
        self.game_state = {
            "Environment": {
                "Actors": [
                    {
                        "ActorName": "CultivateChamber_1",
                        "Inventory": {"1001": {"count": 10, "name": "棉花"}},
                        "CultivateInfo": {"CurrentPhase": "ECultivatePhase::ECP_WaitingToPlant"},
                        "WorkProgress": 0
                    },
                    {
                        "ActorName": "WorkStation",
                        "TaskList": {"2001": 10}
                    }
                ]
            }
        }

    def test_inventory_count_equal(self):
        goal = Goal("CultivateChamber_1", "Inventory", "1001", "==", {"count": 10, "name": "棉花"})
        self.assertTrue(goal.is_satisfied(self.game_state))

    def test_cultivate_phase(self):
        goal = Goal("CultivateChamber_1", "CultivateInfo", "CurrentPhase", "==", "ECultivatePhase::ECP_WaitingToPlant")
        self.assertTrue(goal.is_satisfied(self.game_state))

    def test_tasklist_greater(self):
        goal = Goal("WorkStation", "TaskList", "2001", ">", 5)
        self.assertTrue(goal.is_satisfied(self.game_state))

    def test_not_found_actor(self):
        goal = Goal("NonExist", "Inventory", "1001", "==", {"count": 10, "name": "棉花"})
        self.assertFalse(goal.is_satisfied(self.game_state))

    def test_key_not_exist(self):
        goal = Goal("CultivateChamber_1", "Inventory", "9999", "==", {"count": 10})
        self.assertFalse(goal.is_satisfied(self.game_state))

if __name__ == "__main__":
    unittest.main()
