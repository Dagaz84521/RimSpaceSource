"""
LLM服务器 - 精简版，用于重构
只保留基本的Flask路由和数据结构
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
from typing import Dict, Optional
from agent_manager import RimSpaceAgent
from blackboard import Blackboard, BlackboardTask, Goal
from rimspace_enum import EInteractionType, ECultivatePhase
from planner import Planner
from config import MEAL_MIN_STOCK
from game_data_manager import GameDataManager
from perceiver import perceive_environment_tasks
import os
import itemid_to_name

app = Flask(__name__)
CORS(app)

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "Data")
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "Log")
os.makedirs(LOG_DIR, exist_ok=True)
_server_log_path = os.path.join(
    LOG_DIR,
    f"Server_{datetime.now().strftime('%y%m%d%H-%M-%S')}.log",
)

# 游戏状态缓存
game_state_cache: Dict = {}

# 黑板任务管理
Blackboard_Instance = Blackboard()

# 全局Planner实例用于依赖分解
Global_Planner = Planner(Blackboard_Instance)

# 一些可能会删除的测试代码
def _server_log(message: str) -> None:
    """Append message to server log file (blackboard/decision only)."""
    try:
        with open(_server_log_path, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except Exception:
        pass


# perceive_environment_tasks 已移动到 perceiver.py

def _get_goal_current_value(goal, environment):
    """从环境中获取Goal的当前值，支持各种属性类型（Inventory/TaskList/CultivateInfo）"""
    if not goal or not hasattr(goal, 'target_actor'):
        return None
    
    # 查找目标Actor
    actors = environment.get("Actors", [])
    if isinstance(actors, dict):
        actors = list(actors.values())
    
    target_actor = next((a for a in actors if a.get("ActorName") == goal.target_actor), None)
    if not target_actor:
        return None
    
    # 获取指定属性
    prop = target_actor.get(goal.property_type)
    if prop is None:
        return None
    
    # 根据属性类型和key来获取值
    if goal.key is None:
        # 没有指定key，返回整个属性（通常用于非dict的属性）
        return prop
    
    if isinstance(prop, dict):
        # 处理dict属性（Inventory、TaskList等）
        return prop.get(goal.key, 0)
    else:
        # 非dict属性（如CultivateInfo的CurrentPhase），返回整个属性值进行比较
        return prop


def get_blackboard() -> list:
    """获取当前黑板上的所有任务"""
    return Blackboard_Instance


def _print_blackboard_tasks(environment=None) -> None:
    """打印黑板任务到控制台，包括Goal完成情况和依赖关系"""
    tasks = Blackboard_Instance.tasks
    if not tasks:
        line = "[Blackboard] 任务列表: (empty)"
        print(line)
        _server_log(line)
    else:
        header = "[Blackboard] 任务列表:"
        print(header)
        _server_log(header)
        
        # 包装 environment 以符合 Goal.is_satisfied 的期望格式
        wrapped_env = None
        if environment:
            wrapped_env = {"Environment": environment} if "Environment" not in environment else environment
        
        # 构建task_id到任务的映射
        # task_map = {t.task_id: t for t in tasks}
        
        for idx, task in enumerate(tasks, start=1):
            desc = task.description if hasattr(task, "description") else str(task)
            skill = task.required_skill if hasattr(task, "required_skill") and task.required_skill else "None"
            
            # 追加Goal完成情况
            # goal_status = ""
            # if hasattr(task, "goal") and task.goal and wrapped_env:
            #     current = _get_goal_current_value(task.goal, environment)
            #     target = task.goal.value if hasattr(task.goal, 'value') else "?"
            #     if current is not None:
            #         goal_status = f" [Goal: {current}/{target}]"
            
            # 追加前置条件信息
            prep_status = ""
            if hasattr(task, "preconditions") and task.preconditions and wrapped_env:
                unmet_conditions = []
                for cond in task.preconditions:
                    if not cond.is_satisfied(wrapped_env):
                        # 格式：Actor.Property[Key] operator value
                        cond_str = f"{cond.target_actor}.{cond.property_type}[{cond.key}] {cond.operator} {cond.value}"
                        unmet_conditions.append(cond_str)
                
                if unmet_conditions:
                    prep_status = f" [Preconditions Unmet: {', '.join(unmet_conditions)}]"
                else:
                    prep_status = " [✓ All Preconditions Met]"
            elif hasattr(task, "preconditions") and task.preconditions:
                prep_status = f" [Preconditions: {len(task.preconditions)} items]"
            
            # print(f"    {idx}. [{skill}] {desc}{goal_status}{prep_status}")
            line = f"    {idx}. [{skill}] {desc}{prep_status}"
            print(line)
            _server_log(line)


# ========== 数据加载辅助函数 ==========
def load_item_data() -> Dict:
    """加载物品数据"""
    try:
        item_path = os.path.join(DATA_DIR, "Item.json")
        if os.path.exists(item_path):
            with open(item_path, 'r', encoding='utf-8') as f:
                items = json.load(f)
                # print(f"[数据加载] 已加载 {len(items)} 个物品")
                return {item["ItemID"]: item for item in items}
    except Exception as e:
        # print(f"[错误] 加载物品数据失败: {e}")
        return {}


def load_task_data() -> list:
    """加载任务配方数据"""
    try:
        task_path = os.path.join(DATA_DIR, "Task.json")
        if os.path.exists(task_path):
            with open(task_path, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                # print(f"[数据加载] 已加载 {len(tasks)} 个任务配方")
                return tasks
    except Exception as e:
        # print(f"[错误] 加载任务数据失败: {e}")
        return []   

# ========== Agents ==============
agents = {}



# ========== Flask路由 ==========
@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "running",
        "message": "LLM Server is running (Minimal Version)"
    }), 200


@app.route('/UpdateGameState', methods=['POST'])
def update_game_state():
    """
    更新游戏状态缓存
    游戏会定期发送世界状态
    """
    try:
        data = request.get_json()
        game_state_cache.update(data)
        
        # print(f"[UpdateGameState] 时间: {data.get('GameTime', 'N/A')}")
        
        return jsonify({
            "status": "success",
            "message": "Game state updated"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/GetInstruction', methods=['POST'])
def get_instruction():
    """
    核心接口：为指定角色返回下一步指令
    
    请求格式:
    {
        "TargetAgent": "角色名称",
        "GameTime": "游戏时间",
        "Characters": {...},
        "Environment": {...}
    }
    
    返回格式:
    {
        "CharacterName": "角色名称",
        "CommandType": "Move/Take/Put/Use/Wait",
        "TargetName": "目标名称",
        "ParamID": 物品或配方ID,
        "Count": 数量,
        "Decision": {
            "action": "高级动作名称",
            "params": {...},
            "reasoning": "决策理由"
        },
        "RemainingSteps": 剩余步骤数
    }
    """
    try:
        data = request.get_json()
        
        # 解析请求
        character_name = data.get("TargetAgent", "")
        if not character_name:
            return jsonify({
                "status": "error",
                "message": "Missing TargetAgent"
            }), 400
        
        # 获取游戏状态
        game_time = data.get("GameTime", "")
        characters_data = data.get("Characters", {}).get("Characters", [])
        environment = data.get("Environment", {})

        # 从列表中查找当前角色的数据
        current_char_data = next((c for c in characters_data if c.get("CharacterName") == character_name), {})
        
        # ==========================================
        # 先更新黑板以移除已完成任务，再交给感知器生成新任务
        Blackboard_Instance.update(data)
        perceive_environment_tasks(environment, Blackboard_Instance, Global_Planner, MEAL_MIN_STOCK)
        _print_blackboard_tasks(environment)
        # ==========================================
        
        # print(f"\n[GetInstruction] 角色: {character_name}, 时间: {game_time}")
        
        # ====== TODO: 在这里实现你的决策逻辑 ======
        # 示例：检查角色状态
        # character_info = characters.get("Characters", [])
        # environment_data = environment

        if character_name not in agents:
            agents[character_name] = RimSpaceAgent(character_name, character_name.lower(), Blackboard_Instance)
        agent = agents[character_name]
        decision = agent.make_decision(
            current_char_data,
            environment
        )
        line = f"[{character_name} 决策] {decision}"
        print(line)
        _server_log(line)
        return jsonify(decision), 200
        # 目前返回简单的Wait指令
        # response = create_wait_command(
        #     character_name,
        #     reasoning="精简版服务器 - 等待实现决策逻辑",
        #     wait_time=60  # 等待60分钟
        # )
        
        # print(f"[返回指令] {response}")
        # return jsonify(response), 200
        
    except Exception as e:
        import traceback
        # print(f"[错误] {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ========== 辅助函数 ==========
def create_wait_command(character_name: str, reasoning: str = "", wait_time: int = 0) -> Dict:
    """创建Wait指令"""
    return {
        "CharacterName": character_name,
        "CommandType": "Wait",
        "TargetName": "",
        "ParamID": wait_time,
        "Count": 0,
        "Decision": {
            "action": "Wait",
            "params": {"wait_time": wait_time},
            "reasoning": reasoning
        },
        "RemainingSteps": 0
    }


def create_move_command(character_name: str, target_name: str, reasoning: str = "") -> Dict:
    """创建Move指令"""
    return {
        "CharacterName": character_name,
        "CommandType": "Move",
        "TargetName": target_name,
        "ParamID": 0,
        "Count": 0,
        "Decision": {
            "action": "Move",
            "params": {"target": target_name},
            "reasoning": reasoning
        },
        "RemainingSteps": 0
    }


def create_use_command(character_name: str, target_name: str, param_id: int = 0, reasoning: str = "") -> Dict:
    """创建Use指令"""
    return {
        "CharacterName": character_name,
        "CommandType": "Use",
        "TargetName": target_name,
        "ParamID": param_id,
        "Count": 0,
        "Decision": {
            "action": "Use",
            "params": {"target": target_name, "param_id": param_id},
            "reasoning": reasoning
        },
        "RemainingSteps": 0
    }


# ========== 服务器启动 ==========
if __name__ == '__main__':
    # print("=" * 60)
    # print("  RimSpace LLM Server - 精简版 (用于重构)")
    # print("=" * 60)
    # print(f"  监听地址: http://127.0.0.1:5000")
    # print(f"  数据目录: {DATA_DIR}")
    # print()
    # print("  可用路由:")
    # print("    GET  /health          - 健康检查")
    # print("    POST /UpdateGameState - 更新游戏状态")
    # print("    POST /GetInstruction  - 获取角色指令")
    # print("=" * 60)
    # print()
    
    # 启动Flask服务器
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )


