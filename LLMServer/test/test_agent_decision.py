"""
测试 LLM Server 的 Agent 决策功能
通过 HTTP 请求向服务器发送真实游戏 JSON 数据
"""
import requests
import json
import os
from pathlib import Path


# ==================== 配置 ====================
SERVER_URL = "http://127.0.0.1:5000"
LOG_FILE_PATH = "Log/ServerReceive/InstructionRequest_Farmer_20260128_163229.json"


# ==================== 数据加载 ====================
def load_test_data_from_file():
    """从实际的日志文件加载测试数据"""
    current_dir = Path(__file__).parent  # test 目录
    source_dir = current_dir.parent.parent  # Source 目录
    log_file = source_dir / LOG_FILE_PATH
    
    if log_file.exists():
        print(f"✅ 从文件加载测试数据: {log_file.name}")
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print(f"⚠️  找不到日志文件: {log_file}")
        print("使用内置测试数据...")
        return load_builtin_test_data()


def load_builtin_test_data():
    """内置的测试数据（备用）"""
    return {
        "RequestType": "GetInstruction",
        "TargetAgent": "Farmer",
        "GameTime": "Day 1  06:05",
        "Environment": {
            "Actors": [
                {
                    "ActorName": "CultivateChamber_1",
                    "ActorType": "EInteractionType::EAT_CultivateChamber",
                    "Inventory": {"items": []},
                    "CultivatePhase": "ECultivatePhase::ECP_WaitingToPlant",
                    "TargetCultivateType": "ECultivateType::ECT_Cotton",
                    "CurrentCultivateType": "ECultivateType::ECT_None",
                    "GrowthProgress": 0,
                    "GrowthMaxProgress": 24,
                    "WorkProgress": 0,
                    "WorkloadMax": 10,
                    "HasWorker": False
                },
                {
                    "ActorName": "Storage",
                    "ActorType": "EInteractionType::EAT_None",
                    "Inventory": {
                        "items": [
                            {"id": 1001, "count": 10, "name": "棉花"},
                            {"id": 1002, "count": 50, "name": "玉米"}
                        ]
                    }
                },
                {"ActorName": "Bed_1", "ActorType": "EInteractionType::EAT_Bed"}
            ]
        },
        "Characters": {
            "Characters": [
                {
                    "CharacterName": "Farmer",
                    "CurrentLocation": "None",
                    "ActionState": "ECharacterActionState::Thinking",
                    "Inventory": {"items": []},
                    "CharacterStats": {
                        "Hunger": 99.75,
                        "MaxHunger": 100,
                        "Energy": 99.75,
                        "MaxEnergy": 100
                    },
                    "CharacterSkills": {
                        "CanCook": False,
                        "CanFarm": True,
                        "CanCraft": False
                    }
                }
            ]
        }
    }


# ==================== 数据分析辅助函数 ====================
def extract_character_info(game_data, character_name):
    """提取指定角色的信息"""
    characters = game_data.get("Characters", {}).get("Characters", [])
    for char in characters:
        if char.get("CharacterName") == character_name:
            return char
    return None


def count_pending_tasks(game_data):
    """统计待处理任务数"""
    actors = game_data.get("Environment", {}).get("Actors", [])
    tasks = []
    
    for actor in actors:
        actor_name = actor.get("ActorName", "")
        actor_type = actor.get("ActorType", "")
        
        # 检查种植任务
        if "CultivateChamber" in actor_name:
            phase = actor.get("CultivatePhase", "")
            if "WaitingToPlant" in phase:
                target_crop = actor.get("TargetCultivateType", "").split("::")[-1]
                tasks.append({
                    "type": "Plant",
                    "target": actor_name,
                    "crop": target_crop
                })
    
    return tasks


# ==================== HTTP 请求函数 ====================
def check_server_health(server_url=SERVER_URL):
    """检查服务器健康状态"""
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 服务器运行正常")
            print(f"   状态: {data.get('status')}")
            print(f"   信息: {data.get('message')}")
            return True
        else:
            print(f"⚠️  服务器响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务器: {server_url}")
        return False
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False


def send_get_instruction(json_data, server_url=SERVER_URL):
    """向服务器发送 GetInstruction 请求"""
    endpoint = f"{server_url}/GetInstruction"
    
    try:
        print(f"\n发送请求到: {endpoint}")
        print(f"请求内容:")
        print(f"  - RequestType: {json_data.get('RequestType')}")
        print(f"  - TargetAgent: {json_data.get('TargetAgent')}")
        print(f"  - GameTime: {json_data.get('GameTime')}")
        
        response = requests.post(
            endpoint,
            json=json_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\n服务器响应:")
        print(f"  - 状态码: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  - 错误内容: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务器 {server_url}")
        return None
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时 (30秒)")
        return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


# ==================== 测试函数 ====================
def test_data_validation():
    """测试1: 数据格式验证（离线）"""
    print("=" * 70)
    print("测试 1: 数据格式验证")
    print("=" * 70)
    
    game_data = load_test_data_from_file()
    
    if not game_data:
        print("❌ 无法加载测试数据")
        return False
    
    # 验证必需字段
    required_fields = ["RequestType", "TargetAgent", "GameTime", "Environment", "Characters"]
    missing = [field for field in required_fields if field not in game_data]
    
    if missing:
        print(f"❌ 缺少必需字段: {missing}")
        return False
    
    print("✅ 数据格式验证通过")
    print(f"\n数据摘要:")
    print(f"  - 请求类型: {game_data.get('RequestType')}")
    print(f"  - 目标角色: {game_data.get('TargetAgent')}")
    print(f"  - 游戏时间: {game_data.get('GameTime')}")
    
    # 角色信息
    char_info = extract_character_info(game_data, game_data.get('TargetAgent'))
    if char_info:
        stats = char_info.get('CharacterStats', {})
        print(f"\n角色状态:")
        print(f"  - 饥饿度: {stats.get('Hunger', 0):.2f}/{stats.get('MaxHunger', 100)}")
        print(f"  - 精力值: {stats.get('Energy', 0):.2f}/{stats.get('MaxEnergy', 100)}")
        print(f"  - 当前状态: {char_info.get('ActionState', 'Unknown')}")
    
    # 任务统计
    tasks = count_pending_tasks(game_data)
    if tasks:
        print(f"\n待处理任务: {len(tasks)} 个")
        for i, task in enumerate(tasks[:5], 1):
            print(f"  {i}. {task['type']} {task['crop']} at {task['target']}")
        if len(tasks) > 5:
            print(f"  ... 还有 {len(tasks) - 5} 个任务")
    
    return True


def test_server_connection():
    """测试2: 服务器连接测试"""
    print("\n" + "=" * 70)
    print("测试 2: 服务器连接检查")
    print("=" * 70)
    
    is_healthy = check_server_health()
    
    if not is_healthy:
        print("\n提示: 请先启动 LLM Server")
        print("命令: python .\\LLMServer\\llm_server.py")
    
    return is_healthy


def test_get_instruction_request():
    """测试3: 发送 GetInstruction 请求"""
    print("\n" + "=" * 70)
    print("测试 3: 发送 GetInstruction 请求")
    print("=" * 70)
    
    game_data = load_test_data_from_file()
    
    if not game_data:
        print("❌ 无法加载测试数据")
        return False
    
    response = send_get_instruction(game_data)
    
    if not response:
        print("\n❌ 请求失败")
        return False
    
    print("\n✅ 请求成功!")
    print("\n服务器返回的指令:")
    print("-" * 70)
    print(json.dumps(response, indent=2, ensure_ascii=False))
    print("-" * 70)
    
    # 验证响应格式
    print("\n验证响应格式:")
    required_fields = ["CharacterName", "CommandType"]
    
    all_valid = True
    for field in required_fields:
        if field in response:
            print(f"  ✅ {field}: {response[field]}")
        else:
            print(f"  ❌ 缺少字段: {field}")
            all_valid = False
    
    optional_fields = ["TargetName", "ParamID", "Count", "Decision"]
    for field in optional_fields:
        if field in response:
            value = response[field]
            if field == "Decision" and isinstance(value, dict):
                print(f"  ✅ {field}:")
                for k, v in value.items():
                    print(f"      - {k}: {v}")
            else:
                print(f"  ✅ {field}: {value}")
    
    if all_valid:
        print("\n✅ 响应格式完整且正确!")
    else:
        print("\n⚠️  响应格式不完整")
    
    return all_valid


# ==================== 主测试流程 ====================
def main():
    """主测试流程"""
    print("\n" + "🚀" * 35)
    print("         RimSpace LLM Server 测试工具")
    print("🚀" * 35)
    print("\n功能: 向 LLM Server 发送真实游戏 JSON 数据并验证响应")
    print(f"服务器地址: {SERVER_URL}")
    print("=" * 70)
    
    # 测试1: 数据验证
    if not test_data_validation():
        print("\n❌ 数据验证失败，终止测试")
        return False
    
    # 测试2: 服务器连接
    if not test_server_connection():
        print("\n❌ 服务器未运行，无法继续测试")
        return False
    
    # 等待用户确认
    print("\n" + "=" * 70)
    input("按 Enter 键继续发送测试请求...")
    
    # 测试3: 发送请求
    success = test_get_instruction_request()
    
    # 总结
    print("\n" + "=" * 70)
    if success:
        print("✅ 所有测试通过!")
    else:
        print("⚠️  部分测试失败")
    print("=" * 70)
    
    return success


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
