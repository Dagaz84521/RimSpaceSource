"""
LLM数据接收服务器 - 仅用于接收和记录游戏发送的数据
端口: 5001
功能: 接收游戏状态、命令执行结果等数据，并记录到日志
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
from typing import Dict, Optional

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 日志配置
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "Log", "ServerReceive")
os.makedirs(LOG_DIR, exist_ok=True)

# 数据缓存（用于调试查看）
latest_game_state: Dict = {}
command_history: list = []
MAX_HISTORY_SIZE = 100


def log_to_file(log_type: str, data: Dict):
    """将接收到的数据记录到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{log_type}_{timestamp}.json"
    filepath = os.path.join(LOG_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[日志] 已保存到 {filename}")
    except Exception as e:
        print(f"[错误] 保存日志失败: {e}")


def print_game_state_summary(data: Dict):
    """打印游戏状态摘要"""
    print(f"\n{'='*60}")
    print(f"[游戏状态] {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    # 游戏时间
    game_time = data.get("GameTime", "未知")
    print(f"游戏时间: {game_time}")
    
    # 角色信息
    characters = data.get("Characters", {})
    if isinstance(characters, dict):
        char_array = characters.get("Characters", [])
        print(f"\n角色数量: {len(char_array)}")
        for char in char_array:
            if isinstance(char, dict):
                name = char.get("CharacterName", "Unknown")
                location = char.get("CurrentLocation", "Unknown")
                stats = char.get("CharacterStats", {})
                hunger = stats.get("Hunger", 0)
                energy = stats.get("Energy", 0)
                print(f"  - {name}: 位置={location}, 饥饿={hunger:.1f}, 精力={energy:.1f}")
    
    # 环境Actor
    environment = data.get("Environment", {})
    if isinstance(environment, dict):
        actors = environment.get("Actors", [])
        print(f"\n环境Actor数量: {len(actors)}")
        for actor in actors[:5]:  # 只显示前5个
            if isinstance(actor, dict):
                name = actor.get("ActorName", "Unknown")
                actor_type = actor.get("ActorType", "Unknown")
                print(f"  - {name} ({actor_type})")
        if len(actors) > 5:
            print(f"  ... 还有 {len(actors) - 5} 个Actor")
    
    # 任务配方
    task_recipes = data.get("TaskRecipes", {})
    if isinstance(task_recipes, dict):
        tasks = task_recipes.get("Tasks", [])
        print(f"\n可用任务配方: {len(tasks)}")
        for task in tasks[:3]:  # 只显示前3个
            if isinstance(task, dict):
                task_name = task.get("TaskName", "Unknown")
                facility = task.get("RequiredFacility", "Unknown")
                print(f"  - {task_name} (需要: {facility})")
        if len(tasks) > 3:
            print(f"  ... 还有 {len(tasks) - 3} 个任务")
    
    print(f"{'='*60}\n")


def print_command_result(data: Dict):
    """打印命令执行结果"""
    character_name = data.get("CharacterName", "Unknown")
    result = data.get("LastCommandResult", {})
    
    if not result:
        return
    
    success = result.get("Success", True)
    message = result.get("Message", "")
    failure_reason = result.get("FailureReason", "")
    
    print(f"\n{'='*60}")
    print(f"[命令执行反馈] {character_name}")
    print(f"{'='*60}")
    
    if success:
        print(f"✓ 成功: {message}")
    else:
        print(f"✗ 失败: {failure_reason}")
    
    print(f"{'='*60}\n")


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "ok",
        "message": "Receive-Only Server is running",
        "timestamp": datetime.now().isoformat(),
        "port": 5001,
        "received_commands": len(command_history)
    }), 200


@app.route('/ReceiveGameState', methods=['POST'])
def receive_game_state():
    """
    接收游戏状态数据
    """
    global latest_game_state
    
    try:
        data = request.get_json()
        latest_game_state = data
        
        # 打印摘要
        print_game_state_summary(data)
        
        # 可选：保存到文件（注释掉以减少IO）
        # log_to_file("GameState", data)
        
        return jsonify({
            "status": "success",
            "message": "Game state received",
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"[错误] 接收游戏状态失败: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/ReceiveCommandResult', methods=['POST'])
def receive_command_result():
    """
    接收命令执行结果
    """
    try:
        data = request.get_json()
        
        # 添加时间戳
        data["timestamp"] = datetime.now().isoformat()
        
        # 保存到历史记录
        command_history.append(data)
        if len(command_history) > MAX_HISTORY_SIZE:
            command_history.pop(0)
        
        # 打印结果
        print_command_result(data)
        
        # 保存到文件
        log_to_file("CommandResult", data)
        
        return jsonify({
            "status": "success",
            "message": "Command result received"
        }), 200
        
    except Exception as e:
        print(f"[错误] 接收命令结果失败: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/GetInstruction', methods=['POST'])
def get_instruction():
    """
    接收角色请求指令的数据（带上次执行结果）
    只接收和记录数据，返回Wait指令让游戏继续运行
    """
    try:
        data = request.get_json()
        character_name = data.get("TargetAgent", "Unknown")
        
        print(f"\n{'='*60}")
        print(f"[指令请求] {character_name} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        # 显示上次命令结果
        last_result = data.get("LastCommandResult", {})
        if last_result:
            success = last_result.get("Success", True)
            message = last_result.get("Message", "")
            failure_reason = last_result.get("FailureReason", "")
            
            if success and message:
                print(f"✓ 上次执行: {message}")
            elif not success:
                print(f"✗ 上次失败: {failure_reason}")
        
        # 显示角色状态
        characters = data.get("Characters", {})
        if isinstance(characters, dict):
            char_array = characters.get("Characters", [])
            for char in char_array:
                if isinstance(char, dict) and char.get("CharacterName") == character_name:
                    stats = char.get("CharacterStats", {})
                    hunger = stats.get("Hunger", 100)
                    energy = stats.get("Energy", 100)
                    location = char.get("CurrentLocation", "Unknown")
                    print(f"位置: {location}")
                    print(f"饥饿: {hunger:.1f}/100, 精力: {energy:.1f}/100")
                    break
        
        print(f"{'='*60}\n")
        
        # 保存到文件
        log_to_file(f"InstructionRequest_{character_name}", data)
        
        # 返回Wait指令（让游戏继续运行）
        return jsonify({
            "CharacterName": character_name,
            "CommandType": "Wait",
            "TargetName": "",
            "ParamID": 60,  # 等待60分钟
            "Count": 0
        }), 200
        
    except Exception as e:
        print(f"[错误] 处理指令请求失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/GetLatestState', methods=['GET'])
def get_latest_state():
    """
    获取最新缓存的游戏状态（调试用）
    """
    return jsonify(latest_game_state), 200


@app.route('/GetCommandHistory', methods=['GET'])
def get_command_history():
    """
    获取命令执行历史（调试用）
    """
    return jsonify({
        "total": len(command_history),
        "history": command_history[-20:]  # 返回最近20条
    }), 200


@app.route('/ClearHistory', methods=['POST'])
def clear_history():
    """
    清空历史记录
    """
    global command_history
    command_history = []
    return jsonify({
        "status": "success",
        "message": "History cleared"
    }), 200


if __name__ == '__main__':
    print("="*60)
    print("RimSpace 数据接收服务器 (Receive-Only)")
    print("="*60)
    print(f"端口: 5001")
    print(f"日志目录: {LOG_DIR}")
    print("="*60)
    print("\n接口列表:")
    print("  - GET  /health                  : 健康检查")
    print("  - POST /GetInstruction          : 接收指令请求（返回Wait）[主要]")
    print("  - POST /ReceiveGameState        : 接收游戏状态（可选）")
    print("  - POST /ReceiveCommandResult    : 接收命令执行结果（可选）")
    print("  - GET  /GetLatestState          : 获取最新状态（调试）")
    print("  - GET  /GetCommandHistory       : 获取命令历史（调试）")
    print("  - POST /ClearHistory            : 清空历史记录")
    print("="*60 + "\n")
    print("提示: 该服务器仅接收数据，不做AI决策")
    print("      所有角色将收到Wait指令（等待60分钟）\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
