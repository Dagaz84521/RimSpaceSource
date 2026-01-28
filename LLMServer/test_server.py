"""
测试脚本 - 验证LLM服务器功能
"""
import requests
import json

# 服务器地址
SERVER_URL = "http://localhost:5000"

def test_health():
    """测试健康检查"""
    print("\n=== 测试健康检查 ===")
    response = requests.get(f"{SERVER_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200

def test_get_instruction():
    """测试获取指令"""
    print("\n=== 测试获取指令 ===")
    
    # 模拟游戏状态
    game_state = {
        "TargetAgent": "TestCharacter",
        "GameTime": "Day 1, 08:30",
        "Environment": {
            "Storage_1": {
                "Type": "Storage",
                "Inventory": [
                    {"ItemID": 1, "Count": 10},
                    {"ItemID": 2, "Count": 5}
                ]
            },
            "Bed_1": {
                "Type": "Bed",
                "Inventory": []
            },
            "Stove_1": {
                "Type": "Stove",
                "Inventory": []
            }
        },
        "Characters": {
            "TestCharacter": {
                "Hunger": 25,  # 饥饿
                "Energy": 80,
                "Position": "Storage_1",
                "Inventory": []
            },
            "Chef": {
                "Hunger": 80,
                "Energy": 70,
                "Position": "Stove_1",
                "Inventory": []
            }
        },
        "TaskRecipes": [
            {
                "TaskID": 1,
                "TaskName": "煮饭",
                "ProductID": 1,
                "TaskWorkload": 10,
                "Ingredients": [{"ItemID": 2, "Count": 2}],
                "RequiredFacility": "Stove"
            }
        ],
        "ItemDatabase": {
            "1": {"ItemID": 1, "ItemName": "米饭"},
            "2": {"ItemID": 2, "ItemName": "大米"}
        }
    }
    
    response = requests.post(
        f"{SERVER_URL}/GetInstruction",
        json=game_state,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200

def test_blackboard():
    """测试黑板"""
    print("\n=== 测试黑板状态 ===")
    response = requests.get(f"{SERVER_URL}/GetBlackboard")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 200

def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("LLM Server 测试")
    print("="*60)
    
    tests = [
        ("健康检查", test_health),
        ("获取指令", test_get_instruction),
        ("黑板状态", test_blackboard)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n[错误] {name} 测试失败: {e}")
            results.append((name, False))
    
    # 打印结果
    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status} - {name}")
    print("="*60)

if __name__ == "__main__":
    run_all_tests()
