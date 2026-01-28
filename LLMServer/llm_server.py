"""
LLM服务器 - 精简版，用于重构
只保留基本的Flask路由和数据结构
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from typing import Dict, Optional
from agent_manager import RimSpaceAgent
import os

app = Flask(__name__)
CORS(app)

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "Data")

# 游戏状态缓存
game_state_cache: Dict = {}

# 一些可能会删除的测试代码
def perceive_environment_tasks(environment_data):
    """
    感知层：扫描环境中的 Actor 状态，自动生成隐式任务并注入到黑板中。
    解决"游戏还没做任务发布系统"的问题。
    """
    generated_tasks = []
    
    # 获取环境中的所有 Actor
    actors = environment_data.get("Actors", [])
    if isinstance(actors, dict): # 处理一下数据结构可能的不一致（列表或字典）
        actors = list(actors.values()) # 如果是 {"ActorName": {...}} 的形式
    
    # 遍历所有 Actor
    # for actor in actors:
    #     # 提取关键字段（使用 .get 防止报错）
    #     actor_name = actor.get("ActorName", "Unknown")
    #     actor_type = actor.get("ActorType", "")
        
    #     # === 硬编码逻辑：检测培养舱状态 ===
    #     # 检查是否是培养舱
    #     if "CultivateChamber" in actor_type:
    #         phase = actor.get("CultivatePhase", "")
    #         target_crop = actor.get("TargetCultivateType", "")
    #         has_worker = actor.get("HasWorker", False)
            
    #         # 核心判断：处于“等待种植”且“没有工人”
    #         if "ECP_WaitingToPlant" in phase and not has_worker:
                
    #             # 解析作物类型，映射为 TaskID (参考 Task.json)
    #             task_id = 0
    #             crop_name = "Unknown"
                
    #             if "ECT_Cotton" in target_crop:
    #                 task_id = 1001 # 种植棉花
    #                 crop_name = "Cotton"
    #             elif "ECT_Corn" in target_crop:
    #                 task_id = 1002 # 种植玉米
    #                 crop_name = "Corn"
                
    #             if task_id > 0:
    #                 # 生成一个虚拟的黑板任务
    #                 virtual_task = {
    #                     "TaskID": task_id,
    #                     "TaskName": f"Plant {crop_name} at {actor_name}", # 给 LLM 看的自然语言
    #                     "TaskType": "Plant",
    #                     "TargetName": actor_name, # 重要：告诉 Agent 去哪里
    #                     "Priority": "High" # 既然设定了种植，优先级通常较高
    #                 }
    #                 generated_tasks.append(virtual_task)
    #                 print(f"[感知层] 检测到种植需求: {virtual_task['TaskName']}")
    virtual_task = {
        "TaskID": 1,
        "TaskName": "Transport 50 cotton to WorkStation",
        "TaskType": "Transport",
        "TargetName": "WorkStation",
        "Priority": "Low"
    }
    generated_tasks.append(virtual_task)
    return generated_tasks


# ========== 数据加载辅助函数 ==========
def load_item_data() -> Dict:
    """加载物品数据"""
    try:
        item_path = os.path.join(DATA_DIR, "Item.json")
        if os.path.exists(item_path):
            with open(item_path, 'r', encoding='utf-8') as f:
                items = json.load(f)
                print(f"[数据加载] 已加载 {len(items)} 个物品")
                return {item["ItemID"]: item for item in items}
    except Exception as e:
        print(f"[错误] 加载物品数据失败: {e}")
    return {}


def load_task_data() -> list:
    """加载任务配方数据"""
    try:
        task_path = os.path.join(DATA_DIR, "Task.json")
        if os.path.exists(task_path):
            with open(task_path, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                print(f"[数据加载] 已加载 {len(tasks)} 个任务配方")
                return tasks
    except Exception as e:
        print(f"[错误] 加载任务数据失败: {e}")
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
        
        print(f"[UpdateGameState] 时间: {data.get('GameTime', 'N/A')}")
        
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
        characters = data.get("Characters", {})
        environment = data.get("Environment", {})
        # ==========================================
        # 插入点：调用感知层，生成硬编码任务
        
        # 1. 提取现有的黑板任务（如果有）
        blackboard = data.get("Blackboard", {}).get("Tasks", [])
        
        # 2. 生成新任务（基于 Actor 状态）
        auto_tasks = perceive_environment_tasks(environment)
        
        # 3. 合并任务
        if auto_tasks:
            blackboard.extend(auto_tasks)
            # 将合并后的黑板写回 data，以便 Agent 能读到
            if "Blackboard" not in data:
                data["Blackboard"] = {}
            data["Blackboard"] = blackboard
        environment["Blackboard"] = blackboard
        # ===========================================
        
        print(f"\n[GetInstruction] 角色: {character_name}, 时间: {game_time}")
        
        # ====== TODO: 在这里实现你的决策逻辑 ======
        # 示例：检查角色状态
        # character_info = characters.get("Characters", [])
        # environment_data = environment

        if character_name not in agents:
            agents[character_name] = RimSpaceAgent(character_name, character_name.lower())
        agent = agents[character_name]
        decision = agent.make_decision(
            characters.get(character_name, {}),
            environment
        )
        print(f"[决策] {decision}")
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
        print(f"[错误] {e}")
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
    print("=" * 60)
    print("  RimSpace LLM Server - 精简版 (用于重构)")
    print("=" * 60)
    print(f"  监听地址: http://127.0.0.1:5000")
    print(f"  数据目录: {DATA_DIR}")
    print()
    print("  可用路由:")
    print("    GET  /health          - 健康检查")
    print("    POST /UpdateGameState - 更新游戏状态")
    print("    POST /GetInstruction  - 获取角色指令")
    print("=" * 60)
    print()
    
    # 启动Flask服务器
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )


