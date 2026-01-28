"""
初始场景单独测试
模拟Farmer、Crafter、Chef三个角色的正常工作场景
每轮结束后可以选择是否继续
"""
import requests
import json
import time
import logging
import os
from datetime import datetime
from game_simulator import GameSimulator

SERVER_URL = "http://localhost:5000"

# 配置日志
log_filename = f"test_initial_scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log(message):
    """统一的日志输出"""
    logger.info(message)


def create_initial_game_state():
    """创建初始场景的游戏状态"""
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


def request_instruction(character_name, game_state):
    """请求角色的下一个指令"""
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
    
    try:
        response = requests.post(
            f"{SERVER_URL}/GetInstruction",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if "Decision" in result:
                log(f"  决策: {result['Decision'].get('action', 'Unknown')} - {result['Decision'].get('reasoning', '')}")
            
            return result
        else:
            log(f"❌ 请求失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log(f"❌ 请求异常: {e}")
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
    
    log("")


def save_world_state(round_num, game_state, folder_path):
    """保存世界状态到文件"""
    state_filename = os.path.join(folder_path, "world_state.json")
    
    try:
        # 读取现有数据
        if os.path.exists(state_filename):
            with open(state_filename, 'r', encoding='utf-8') as f:
                all_states = json.load(f)
        else:
            all_states = []
        
        # 添加当前轮次的状态
        round_state = {
            "Round": round_num,
            "GameState": game_state
        }
        all_states.append(round_state)
        
        # 写入文件
        with open(state_filename, 'w', encoding='utf-8') as f:
            json.dump(all_states, f, ensure_ascii=False, indent=2)
        log(f"📄 世界状态已保存到: {state_filename}")
    except Exception as e:
        log(f"❌ 保存世界状态失败: {e}")


def save_character_log(character_name, content, folder_path):
    """保存角色日志到文件"""
    char_filename = os.path.join(folder_path, f"{character_name}.txt")
    
    try:
        with open(char_filename, 'a', encoding='utf-8') as f:
            f.write(content + "\n")
    except Exception as e:
        log(f"❌ 保存{character_name}日志失败: {e}")


def check_blackboard():
    """检查黑板状态"""
    log(f"\n{'='*80}")
    log("查看任务黑板")
    log(f"{'='*80}")
    
    try:
        response = requests.get(f"{SERVER_URL}/GetBlackboard", timeout=5)
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
    except Exception as e:
        log(f"❌ 获取黑板异常: {e}")


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


def run_single_round(round_num, game_state, characters, test_folder, simulator):
    """运行单个回合"""
    log(f"\n{'='*80}")
    log(f"回合 {round_num}")
    log(f"{'='*80}")
    
    # 保存世界状态到文件
    save_world_state(round_num, game_state, test_folder)
    
    for character in characters:
        log(f"\n[{character}]")
        
        # 收集角色日志内容
        char_log_content = []
        char_log_content.append(f"{'='*60}")
        char_log_content.append(f"回合 {round_num} - {character}")
        char_log_content.append(f"{'='*60}")
        
        character_info = game_state.get("Characters", {}).get(character, {})
        hunger = character_info.get("Hunger", 100)
        energy = character_info.get("Energy", 100)
        profession = character_info.get("Profession", "Unknown")
        skills = character_info.get("Skills", {})
        
        status_line = f"状态: Hunger={hunger:.1f}, Energy={energy:.1f}, 职业={profession}"
        skills_line = f"技能: {', '.join([k for k, v in skills.items() if v])}"
        
        log(f"  {status_line}")
        log(f"  {skills_line}")
        char_log_content.append(status_line)
        char_log_content.append(skills_line)
        
        instruction = request_instruction(character, game_state)
        if instruction:
            # 记录决策信息
            decision = instruction.get("Decision", {})
            if decision:
                action = decision.get("action", "Unknown")
                reasoning = decision.get("reasoning", "")
                remaining = instruction.get("RemainingSteps", 0)
                
                decision_line = f"💭 高级决策: {action}"
                log(f"  {decision_line}")
                char_log_content.append(decision_line)
                
                if reasoning:
                    reasoning_line = f"   理由: {reasoning}"
                    log(f"  {reasoning_line}")
                    char_log_content.append(reasoning_line)
                
                if remaining > 0:
                    remaining_line = f"   剩余计划步骤: {remaining}"
                    log(f"  {remaining_line}")
                    char_log_content.append(remaining_line)
            
            # 记录单步指令
            cmd = instruction.get("CommandType", "Unknown")
            target = instruction.get("TargetName", "")
            param_id = instruction.get("ParamID", 0)
            count = instruction.get("Count", 0)
            
            cmd_line = ""
            if cmd == "Move":
                cmd_line = f"➜ 单步指令: 移动到 {target}"
            elif cmd == "Take":
                cmd_line = f"➜ 单步指令: 从 {target} 取出物品{param_id} x{count}"
            elif cmd == "Put":
                cmd_line = f"➜ 单步指令: 放入物品{param_id} x{count} 到 {target}"
            elif cmd == "Use":
                if target:
                    cmd_line = f"➜ 单步指令: 使用 {target} (参数:{param_id})"
                else:
                    cmd_line = f"➜ 单步指令: 使用物品{param_id}"
            elif cmd == "Wait":
                cmd_line = f"➜ 单步指令: 等待"
            else:
                cmd_line = f"➜ 单步指令: {cmd} - {instruction}"
            
            log(f"  {cmd_line}")
            char_log_content.append(cmd_line)
            
            # 执行指令并更新游戏状态
            result = simulator.execute_instruction(character, instruction)
            result_line = f"  ✓ 执行结果: {result['message']}" if result['success'] else f"  ✗ 执行失败: {result['message']}"
            log(result_line)
            char_log_content.append(result_line)
            
            time.sleep(0.2)  # 避免请求过快
        else:
            error_line = f"❌ {character} 获取指令失败"
            log(f"  {error_line}")
            char_log_content.append(error_line)
        
        log("")
        char_log_content.append("")
        
        # 保存角色日志到文件
        save_character_log(character, "\n".join(char_log_content), test_folder)
    
    # 显示黑板状态
    check_blackboard()


def main():
    """主函数"""
    log("="*80)
    log("RimSpace 初始场景测试")
    log("="*80)
    log("说明:")
    log("  - Farmer应该种植作物")
    log("  - Crafter应该制作物品")
    log("  - Chef应该制作食物")
    log("  - 每轮结束后可以选择是否继续")
    log(f"\n日志文件: {log_filename}\n")
    
    # 检查服务器
    if not check_server():
        log("\n请先启动LLM服务器！")
        log("运行命令: python .\\LLMServer\\LLMServer.py")
        return
    
    # 创建测试目录
    log_base_dir = "Log"
    if not os.path.exists(log_base_dir):
        os.makedirs(log_base_dir)
    
    test_folder = os.path.join(log_base_dir, f"Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(test_folder, exist_ok=True)
    log(f"📁 测试日志根目录: {test_folder}\n")
    
    # 初始化
    characters = ["Farmer", "Crafter", "Chef"]
    game_state = create_initial_game_state()
    simulator = GameSimulator(game_state)
    round_num = 1
    
    log("📊 初始世界状态:")
    simulator.print_summary()
    
    # 开始测试循环
    while True:
        run_single_round(round_num, game_state, characters, test_folder, simulator)
        
        # 显示当前世界状态摘要
        log("\n📊 当前世界状态:")
        simulator.print_summary()
        
        # 询问是否继续
        log(f"\n{'='*80}")
        choice = input(f"回合 {round_num} 完成！是否继续下一回合？(y/n，直接回车=继续): ").strip().lower()
        
        if choice == 'n':
            log("\n测试结束！")
            break
        elif choice == '' or choice == 'y':
            round_num += 1
            continue
        else:
            log("无效输入，默认继续")
            round_num += 1
            continue
    
    log(f"\n完整日志已保存到: {log_filename}")
    log(f"总共运行了 {round_num} 轮")


if __name__ == "__main__":
    main()
