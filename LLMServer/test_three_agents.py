"""
3 Agent协作测试用例
模拟Farmer、Crafter、Chef三个角色的协作场景
"""
import requests
import json
import time
import logging
from datetime import datetime

SERVER_URL = "http://localhost:5000"

# 配置日志
log_filename = f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
logger = logging.getLogger(__name__)

def log(message):
    """统一的日志输出"""
    logger.info(message)

# 模拟游戏世界状态
def create_game_state(scenario="initial"):
    """创建不同场景的游戏状态"""
    
    if scenario == "initial":
        # 初始场景：仓库有原材料，角色状态良好
        return {
            "GameTime": "Day 1, 08:00",
            "Environment": {
                "Storage": {
                    "Type": "Storage",
                    "Inventory": [
                        {"ItemID": 1001, "ItemName": "Cotton", "Count": 100},
                        {"ItemID": 1002, "ItemName": "Corn", "Count": 100}
                    ]
                },
                "CultivateChamber": {
                    "Type": "CultivateChamber",
                    "Inventory": []
                },
                "WorkStation": {
                    "Type": "WorkStation",
                    "Inventory": []
                },
                "Stove": {
                    "Type": "Stove",
                    "Inventory": []
                },
                "Bed_1": {
                    "Type": "Bed",
                    "Inventory": []
                },
                "Bed_2": {
                    "Type": "Bed",
                    "Inventory": []
                },
                "Bed_3": {
                    "Type": "Bed",
                    "Inventory": []
                }
            },
            "Characters": {
                "Farmer": {
                    "Profession": "Farmer",
                    "Hunger": 80.0,
                    "Energy": 90.0,
                    "Inventory": [],
                    "Skills": {
                        "CanCook": False,
                        "CanFarm": True,
                        "CanCraft": False
                    }
                },
                "Crafter": {
                    "Profession": "Crafter",
                    "Hunger": 85.0,
                    "Energy": 95.0,
                    "Inventory": [],
                    "Skills": {
                        "CanCook": False,
                        "CanFarm": False,
                        "CanCraft": True
                    }
                },
                "Chef": {
                    "Profession": "Chef",
                    "Hunger": 90.0,
                    "Energy": 85.0,
                    "Inventory": [],
                    "Skills": {
                        "CanCook": True,
                        "CanFarm": False,
                        "CanCraft": False
                    }
                }
            },
            "TaskRecipes": [
                {
                    "TaskID": 1001,
                    "TaskName": "种植棉花",
                    "ProductID": 1001,
                    "TaskWorkload": 120,
                    "Ingredients": [],
                    "RequiredFacility": "CultivateChamber"
                },
                {
                    "TaskID": 1002,
                    "TaskName": "种植玉米",
                    "ProductID": 1002,
                    "TaskWorkload": 100,
                    "Ingredients": [],
                    "RequiredFacility": "CultivateChamber"
                },
                {
                    "TaskID": 2001,
                    "TaskName": "生产棉线",
                    "ProductID": 2001,
                    "TaskWorkload": 100,
                    "Ingredients": [{"ItemID": 1001, "Count": 5}],
                    "RequiredFacility": "WorkStation"
                },
                {
                    "TaskID": 2002,
                    "TaskName": "生产布料",
                    "ProductID": 2002,
                    "TaskWorkload": 200,
                    "Ingredients": [{"ItemID": 1001, "Count": 5}],
                    "RequiredFacility": "WorkStation"
                },
                {
                    "TaskID": 2003,
                    "TaskName": "制作套餐",
                    "ProductID": 2003,
                    "TaskWorkload": 150,
                    "Ingredients": [{"ItemID": 1002, "Count": 5}],
                    "RequiredFacility": "Stove"
                },
                {
                    "TaskID": 3001,
                    "TaskName": "生产衣服",
                    "ProductID": 3001,
                    "TaskWorkload": 250,
                    "Ingredients": [
                        {"ItemID": 2002, "Count": 2},
                        {"ItemID": 2001, "Count": 3}
                    ],
                    "RequiredFacility": "WorkStation"
                }
            ],
            "ItemDatabase": {
                "1001": {"ItemID": 1001, "ItemName": "Cotton", "IsFood": False},
                "1002": {"ItemID": 1002, "ItemName": "Corn", "IsFood": False},
                "2001": {"ItemID": 2001, "ItemName": "Thread", "IsFood": False},
                "2002": {"ItemID": 2002, "ItemName": "Cloth", "IsFood": False},
                "2003": {"ItemID": 2003, "ItemName": "Meal", "IsFood": True, "NutritionValue": 80.0},
                "3001": {"ItemID": 3001, "ItemName": "Coat", "IsFood": False}
            }
        }
    
    elif scenario == "hungry":
        # 饥饿场景：所有人都饿了，但没有食物
        state = create_game_state("initial")
        state["GameTime"] = "Day 1, 12:00"
        state["Characters"]["Farmer"]["Hunger"] = 25.0
        state["Characters"]["Crafter"]["Hunger"] = 20.0
        state["Characters"]["Chef"]["Hunger"] = 30.0
        # 仓库没有食物
        state["Environment"]["Storage"]["Inventory"] = [
            {"ItemID": 1001, "ItemName": "Cotton", "Count": 50},
            {"ItemID": 1002, "ItemName": "Corn", "Count": 80}
        ]
        return state
    
    elif scenario == "crafting":
        # 制作场景：Crafter要制作衣服，但WorkStation缺少原料
        state = create_game_state("initial")
        state["GameTime"] = "Day 1, 14:00"
        # 仓库有原料
        state["Environment"]["Storage"]["Inventory"] = [
            {"ItemID": 1001, "ItemName": "Cotton", "Count": 50},
            {"ItemID": 2001, "ItemName": "Thread", "Count": 10},
            {"ItemID": 2002, "ItemName": "Cloth", "Count": 5}
        ]
        # WorkStation没有原料
        state["Environment"]["WorkStation"]["Inventory"] = []
        return state
    
    elif scenario == "tired":
        # 疲惫场景：Farmer精力耗尽
        state = create_game_state("initial")
        state["GameTime"] = "Day 1, 22:00"
        state["Characters"]["Farmer"]["Energy"] = 8.0
        return state
log

def request_instruction(character_name, game_state):
    """请求角色的下一个指令"""
    # 打印角色当前状态
    character_info = game_state.get("Characters", {}).get(character_name, {})
    hunger = character_info.get("Hunger", 100)
    energy = character_info.get("Energy", 100)
    profession = character_info.get("Profession", "Unknown")
    skills = character_info.get("Skills", {})
    
    log(f"  状态: Hunger={hunger:.1f}, Energy={energy:.1f}, 职业={profession}")
    log(f"  技能: {', '.join([k for k, v in skills.items() if v])}")
    
    request_data = {
        "TargetAgent": character_name,
        **game_state
    }
    
    response = requests.post(
        f"{SERVER_URL}/GetInstruction",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        
        # 打印决策信息（如果服务器返回了）
        if "Decision" in result:
            log(f"  决策: {result['Decision'].get('action', 'Unknown')} - {result['Decision'].get('reasoning', '')}")
        
        return result
    else:
        log(f"❌ 请求失败: {response.status_code} - {response.text}")
        return None


def print_instruction(character_name, instruction):
    """打印指令（格式化）"""
    if not instruction:
        return
    
    # 打印决策信息
    decision = instruction.get("Decision", {})
    if decision:
        action = decision.get("action", "Unknown")
        reasoning = decision.get("reasoning", "")
        remaining = instruction.get("RemainingSteps", 0)
        
        log(f"  💭 高级决策: {action}")
        if reasoning:
            log(f"     理由: {reasoning}")
        if remaining > 0:
            log(f"     剩余计划步骤: {remaining}")
    
    # 打印单步指令
    cmd = instruction.get("CommandType", "Unknown")
    target = instruction.get("TargetName", "")
    param_id = instruction.get("ParamID", 0)
    count = instruction.get("Count", 0)
    
    if cmd == "Move":
        log(f"  ➜ 单步指令: 移动到 {target}")
    elif cmd == "Take":
        log(f"  ➜ 单步指令: 从 {target} 取出物品{param_id} x{count}")
    elif cmd == "Put":
        log(f"  ➜ 单步指令: 放入物品{param_id} x{count} 到 {target}")
    elif cmd == "Use":
        if target:
            log(f"  ➜ 单步指令: 使用 {target} (参数:{param_id})")
        else:
            log(f"  ➜ 单步指令: 使用物品{param_id}")
    elif cmd == "Wait":
        log(f"  ➜ 单步指令: 等待")
    else:
        log(f"  ➜ 单步指令: {cmd} - {instruction}")
    
    log("")  # 空行分隔


def test_scenario(scenario_name, game_state, characters, rounds=3):
    """测试一个场景"""
    log(f"\n{'='*80}")
    log(f"测试场景: {scenario_name}")
    log(f"{'='*80}")
    
    for round_num in range(1, rounds + 1):
        log(f"\n--- 回合 {round_num} ---")
        for character in characters:
            log(f"\n[{character}]")
            instruction = request_instruction(character, game_state)
            if instruction:
                print_instruction(character, instruction)
                
                # 模拟指令执行（简化，不真正修改游戏状态）
                time.sleep(0.2)  # 避免请求过快
            else:
                log(f"  ❌ {character} 获取指令失败")


def check_blackboard():
    """检查黑板状态"""
    log(f"\n{'='*80}")
    log("查看任务黑板")
    log(f"{'='*80}")
    
    response = requests.get(f"{SERVER_URL}/GetBlackboard")
    if response.status_code == 200:
        blackboard = response.json()
        log(f"总任务数: {blackboard.get('total_tasks', 0)}")
        log(f"待认领: {blackboard.get('pending_tasks', 0)}")
        log(f"进行中: {blackboard.get('active_tasks', 0)}")
        log(f"已完成: {blackboard.get('completed_tasks', 0)}")
        
        tasks = blackboard.get('tasks', [])
        if tasks:
            log("\n任务列表:")
            for task in tasks:
                status_emoji = {
                    "pending": "⏳",
                    "claimed": "🔵",
                    "in_progress": "🔄",
                    "completed": "✅"
                }.get(task['status'], "❓")
                
                log(f"  {status_emoji} [{task['task_id']}] {task['description']}")
                log(f"     发布者: {task['publisher']}, 认领者: {task.get('claimer', '无')}")
        else:
            log("  (无任务)")
    else:
        log(f"❌ 获取黑板失败: {response.status_code}")


def check_server():
    """检查服务器连接"""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=3)
        if response.status_code == 200:
            health = response.json()
            log(f"✅ 服务器状态: {health.get('status')}")
            log(f"   LLM可用: {health.get('llm_available')}")
            return True
        else:
            log("❌ 服务器连接失败")
            return False
    except Exception as e:
        log(f"❌ 无法连接到服务器: {e}")
        log(f"   请确保服务器运行在 {SERVER_URL}")
        return False


def test_1_initial_scenario():
    """测试1: 初始场景 - 正常工作"""
    log("\n\n" + "="*80)
    log("🧪 测试1: 初始场景 - 三个角色正常工作")
    log("="*80)
    log("说明:")
    log("  - Farmer应该种植作物")
    log("  - Crafter应该制作物品")
    log("  - Chef应该制作食物")
    
    characters = ["Farmer", "Crafter", "Chef"]
    game_state = create_game_state("initial")
    test_scenario("初始场景", game_state, characters, rounds=3)
    check_blackboard()
    
    log("\n测试1完成!")


def test_2_hungry_scenario():
    """测试2: 饥饿场景 - 测试食物协作"""
    log("\n\n" + "="*80)
    log("🧪 测试2: 饥饿场景 - 测试食物请求协作")
    log("="*80)
    log("说明:")
    log("  - 所有人都饿了，但没有现成的食物")
    log("  - 预期: 非厨师会发布烹饪任务，Chef会认领")
    
    characters = ["Farmer", "Crafter", "Chef"]
    game_state = create_game_state("hungry")
    test_scenario("饥饿场景", game_state, characters, rounds=4)
    check_blackboard()
    
    log("\n测试2完成!")


def test_3_crafting_scenario():
    """测试3: 制作场景 - 测试搬运协作"""
    log("\n\n" + "="*80)
    log("🧪 测试3: 制作场景 - 测试物品搬运协作")
    log("="*80)
    log("说明:")
    log("  - Crafter要制作衣服，但WorkStation缺原料")
    log("  - 预期: Crafter会发布搬运任务，其他人可以认领")
    
    game_state = create_game_state("crafting")
    
    # 第一部分：只让Crafter请求指令，看是否发布任务
    log("\n>>> 第一部分: Crafter尝试制作")
    test_scenario("制作场景 - Crafter", game_state, ["Crafter"], rounds=5)
    check_blackboard()
    
    # 第二部分：让其他角色认领任务
    log("\n>>> 第二部分: 其他角色认领任务")
    test_scenario("制作场景 - 其他角色", game_state, ["Farmer", "Chef"], rounds=3)
    check_blackboard()
    
    log("\n测试3完成!")


def test_4_tired_scenario():
    """测试4: 疲惫场景 - 测试紧急状态打断"""
    log("\n\n" + "="*80)
    log("🧪 测试4: 疲惫场景 - 测试紧急状态打断")
    log("="*80)
    log("说明:")
    log("  - Farmer精力极低")
    log("  - 预期: 即使有计划队列，也应该被打断去睡觉")
    
    game_state = create_game_state("tired")
    test_scenario("疲惫场景", game_state, ["Farmer"], rounds=3)
    check_blackboard()
    log("="*80)
    log("RimSpace 3-Agent 协作测试系统")
    log("="*80)
    log(f"日志文件: {log_filename}\n")
    
    # 检查服务器
    if not check_server():
        log("\n请先启动LLM服务器！")
        exit(1)
    
    # 交互式菜单
    while True:
        show_menu()
        choice = input("\n请输入选项 (0-5): ").strip()
        
        if choice == "1":
            test_1_initial_scenario()
            input("\n按回车返回菜单...")
        elif choice == "2":
            test_2_hungry_scenario()
            input("\n按回车返回菜单...")
        elif choice == "3":
            test_3_crafting_scenario()
            input("\n按回车返回菜单...")
        elif choice == "4":
            test_4_tired_scenario()
            input("\n按回车返回菜单...")
        elif choice == "5":
            run_all_tests()
            input("\n按回车返回菜单...")
        elif choice == "0":
            log("\n再见!")
            break
        else:
            log("\n❌ 无效的选项，请重新输入")
    
    log(f"\n完整日志已保存到: {log_filename}")
    log("\n测试4完成!")


def show_menu():
    """显示菜单"""
    log("\n" + "="*80)
    log("RimSpace 3-Agent 协作测试")
    log("="*80)
    log(f"日志文件: {log_filename}")
    log("\n请选择测试场景:")
    log("  1. 初始场景 - 三个角色正常工作")
    log("  2. 饥饿场景 - 测试食物请求协作")
    log("  3. 制作场景 - 测试物品搬运协作")
    log("  4. 疲惫场景 - 测试紧急状态打断")
    log("  5. 运行所有测试")
    log("  0. 退出")
    log("="*80)


def run_all_tests():
    """运行所有测试"""
    log("="*80)
    log("开始运行所有测试...")
    log("="*80)
    
    test_1_initial_scenario()
    input("\n按回车继续下一个测试...")
    
    test_2_hungry_scenario()
    input("\n按回车继续下一个测试...")
    
    test_3_crafting_scenario()
    input("\n按回车继续下一个测试...")
    
    test_4_tired_scenario()
    
    log("\n\n" + "="*80)
    log("所有测试完成！")
    log("="*80)
    log("\n💡 提示:")
    log("  - 查看服务器控制台可以看到详细的决策过程")
    log("  - 黑板任务会在角色间共享")
    log("  - 计划会在验证失败时自动重规划")
    log("  - 紧急状态(Hunger<10 或 Energy<10)会打断当前计划")
    log(f"  - 完整日志已保存到: {log_filename}")


if __name__ == "__main__":
    run_all_tests()
