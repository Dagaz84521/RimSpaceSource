# 培养仓测试服务器
# 模拟 LLM 服务器，按预设顺序返回命令，测试培养仓的完整工作流程
# 用法：python test_cultivate_chamber.py（替代 LLMServer.py 启动）

from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# === 测试命令队列 ===
# 按顺序返回这些命令给游戏
COMMAND_QUEUE = [
    # 阶段1: 移动到培养仓
    {
        "CommandType": "Move",
        "TargetName": "CultivateChamber_1",  # 根据实际游戏中的名称修改
        "ParamID": 0,
        "Count": 0,
        "Description": "移动到培养仓准备种植"
    },
    # 阶段2: 使用培养仓（种植）
    {
        "CommandType": "Use",
        "TargetName": "CultivateChamber_1",
        "ParamID": 0,
        "Count": 0,
        "Description": "开始种植"
    },
    # 阶段3: 等待种植和成长完成（多次等待）
    {
        "CommandType": "Wait",
        "TargetName": "",
        "ParamID": 60,  # 等待60分钟
        "Count": 0,
        "Description": "等待成长（60分钟）"
    },
    {
        "CommandType": "Wait",
        "TargetName": "",
        "ParamID": 60,
        "Count": 0,
        "Description": "等待成长（再60分钟）"
    },
    # 阶段4: 移动到培养仓收获
    {
        "CommandType": "Move",
        "TargetName": "CultivateChamber_1",
        "ParamID": 0,
        "Count": 0,
        "Description": "移动到培养仓准备收获"
    },
    # 阶段5: 使用培养仓（收获）
    {
        "CommandType": "Use",
        "TargetName": "CultivateChamber_1",
        "ParamID": 0,
        "Count": 0,
        "Description": "开始收获"
    },
    # 阶段6: 拾取产出物品
    {
        "CommandType": "Take",
        "TargetName": "",
        "ParamID": 1,  # 棉花的 ItemID，根据实际修改
        "Count": 1,
        "Description": "拾取棉花"
    },
    # 阶段7: 移动到仓库
    {
        "CommandType": "Move",
        "TargetName": "仓库",  # 根据实际游戏中的名称修改
        "ParamID": 0,
        "Count": 0,
        "Description": "移动到仓库"
    },
    # 阶段8: 放下物品
    {
        "CommandType": "Put",
        "TargetName": "",
        "ParamID": 1,
        "Count": 1,
        "Description": "放下棉花到仓库"
    },
]

# 当前命令索引
current_command_index = 0

# 是否循环执行命令队列
LOOP_COMMANDS = False


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    print("[测试服务器] 收到健康检查")
    return "OK", 200


@app.route('/UpdateGameState', methods=['POST'])
def game_state_update():
    """接收游戏状态更新，打印以便观察"""
    data = request.json
    
    print("\n" + "=" * 50)
    print("[游戏状态更新]")
    print("=" * 50)
    
    # 提取关键信息
    game_time = data.get("GameTime", "未知")
    print(f"游戏时间: {game_time}")
    
    # 打印角色状态
    characters = data.get("Characters", {}).get("Characters", [])
    for char in characters:
        name = char.get("CharacterName", "未知")
        action = char.get("ActionState", "未知")
        location = char.get("CurrentLocation", "未知")
        print(f"角色 [{name}]: 状态={action}, 位置={location}")
    
    # 打印培养仓状态（新格式）
    actors = data.get("Environment", {}).get("Actors", [])
    for actor in actors:
        actor_type = actor.get("ActorType", "")
        if "CultivateChamber" in actor_type:
            name = actor.get("ActorName", "未知")
            # 新增的字段
            phase = actor.get("CultivatePhase", "未知")
            # 去掉枚举前缀
            phase = phase.replace("ECultivatePhase::", "")
            target_type = actor.get("TargetCultivateType", "未知").replace("ECultivateType::", "")
            current_type = actor.get("CurrentCultivateType", "未知").replace("ECultivateType::", "")
            growth = actor.get("GrowthProgress", 0)
            max_growth = actor.get("GrowthMaxProgress", 0)
            work_progress = actor.get("WorkProgress", 0)
            workload_max = actor.get("WorkloadMax", 0)
            has_worker = actor.get("HasWorker", False)
            
            print(f"\n培养仓 [{name}]:")
            print(f"  阶段: {phase}")
            print(f"  目标作物: {target_type}")
            print(f"  当前作物: {current_type}")
            print(f"  成长进度: {growth}/{max_growth}")
            print(f"  工作进度: {work_progress}/{workload_max}")
            print(f"  有工人: {'是' if has_worker else '否'}")
    
    print("=" * 50 + "\n")
    
    return jsonify({"status": "received"}), 200


@app.route('/GetInstruction', methods=['POST'])
def get_instruction():
    """返回预设的测试命令"""
    global current_command_index
    
    data = request.json
    target_agent = data.get("TargetAgent", "Unknown")
    game_time = data.get("GameTime", "未知")
    
    print("\n" + "=" * 50)
    print(f"[指令请求] 角色: {target_agent}, 时间: {game_time}")
    print("=" * 50)
    
    # 获取当前命令
    if current_command_index < len(COMMAND_QUEUE):
        cmd = COMMAND_QUEUE[current_command_index]
        description = cmd.get("Description", "")
        
        response = {
            "CharacterName": target_agent,
            "CommandType": cmd["CommandType"],
            "TargetName": cmd["TargetName"],
            "ParamID": cmd["ParamID"],
            "Count": cmd["Count"]
        }
        
        print(f"[命令 {current_command_index + 1}/{len(COMMAND_QUEUE)}] {description}")
        print(f"返回: {json.dumps(response, ensure_ascii=False)}")
        
        current_command_index += 1
        
        # 循环模式
        if LOOP_COMMANDS and current_command_index >= len(COMMAND_QUEUE):
            current_command_index = 0
            print("[提示] 命令队列已循环")
    else:
        # 所有命令执行完毕，返回等待
        response = {
            "CharacterName": target_agent,
            "CommandType": "Wait",
            "TargetName": "",
            "ParamID": 10,
            "Count": 0
        }
        print("[完成] 所有测试命令已执行，进入等待状态")
    
    print("=" * 50 + "\n")
    
    return jsonify(response), 200


@app.route('/reset', methods=['GET'])
def reset_commands():
    """重置命令队列（可通过浏览器访问 http://localhost:5000/reset）"""
    global current_command_index
    current_command_index = 0
    print("[测试服务器] 命令队列已重置")
    return "Command queue reset!", 200


@app.route('/status', methods=['GET'])
def get_status():
    """查看当前状态（可通过浏览器访问 http://localhost:5000/status）"""
    status = {
        "current_index": current_command_index,
        "total_commands": len(COMMAND_QUEUE),
        "next_command": COMMAND_QUEUE[current_command_index] if current_command_index < len(COMMAND_QUEUE) else "完成"
    }
    return jsonify(status), 200


def print_test_plan():
    """打印测试计划"""
    print("\n" + "=" * 60)
    print("培养仓测试服务器 - 测试计划")
    print("=" * 60)
    print("\n预设命令队列:")
    for i, cmd in enumerate(COMMAND_QUEUE):
        print(f"  {i + 1}. [{cmd['CommandType']}] {cmd.get('Description', '')}")
        if cmd['TargetName']:
            print(f"      TargetName: {cmd['TargetName']}")
        if cmd['ParamID']:
            print(f"      ParamID: {cmd['ParamID']}")
    print("\n" + "=" * 60)
    print("使用说明:")
    print("  1. 运行此脚本启动测试服务器")
    print("  2. 启动 UE5 游戏")
    print("  3. 在游戏中设定培养仓种植类型（如种植棉花）")
    print("  4. 观察角色按命令队列执行动作")
    print("")
    print("管理端点:")
    print("  GET  http://localhost:5000/status  - 查看当前状态")
    print("  GET  http://localhost:5000/reset   - 重置命令队列")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    print_test_plan()
    print("服务器启动，监听端口 5000...\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
