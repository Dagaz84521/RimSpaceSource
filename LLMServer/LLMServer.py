from flask import Flask, request, jsonify
import json
import random

app = Flask(__name__)

# === 路由定义 ===

@app.route('/health', methods=['GET'])
def health_check():
    """用于游戏启动时的连接检查"""
    print("收到健康检查请求 (Ping)")
    return "OK", 200

@app.route('/UpdateGameState', methods=['POST'])
def game_state_update():
    data = request.json
    
    # === 新增：格式化打印完整 JSON ===
    print("\n" + "="*20 + " 收到完整 JSON 数据 " + "="*20)
    # indent=4 用于缩进，ensure_ascii=False 确保中文能正常显示
    print(json.dumps(data, indent=4, ensure_ascii=False))
    print("="*60 + "\n")
    # ==============================

    # 下面是你之前的逻辑
    # print(f"收到游戏状态，包含 {len(data.get('Actors', []))} 个Actor") 
    
    # 记得补充返回值，否则 UE5 会报错
    return jsonify({"status": "received"}), 200

@app.route('/GetInstruction', methods=['POST'])
def get_instruction():
    data = request.json
    target_agent = data.get("TargetAgent", "Unknown")
    
    print(f"收到 {target_agent} 的指令请求")
    
    # === 这里编写对接 LLM 的逻辑 ===
    # 模拟一个返回指令，例如让角色去 Move 到 Table
    # 注意：CommandType 的值必须匹配 C++ Enum 的字符串表示
    response_command = {
        "CharacterName": target_agent,
        "CommandType": "Move",  
        "TargetName": "Table", # 确保场景里有叫这个名字的 Actor
        "ParamID": 0,
        "Count": 0
    }
    
    return jsonify(response_command), 200

if __name__ == '__main__':
    # host='0.0.0.0' 允许局域网访问，port=5000 是默认端口
    print("服务器已启动，监听端口 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)