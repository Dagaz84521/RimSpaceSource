from flask import Flask, request, jsonify
import json
import os
from openai import OpenAI

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
    
    # === 格式化打印完整 JSON ===
    print("\n" + "="*20 + " 收到完整 JSON 数据 " + "="*20)
    print(json.dumps(data, indent=4, ensure_ascii=False))
    print("="*60 + "\n")
    
    return jsonify({"status": "received"}), 200


@app.route('/GetInstruction', methods=['POST'])
def get_instruction():
        # LLM 请求失败时的后备指令
    print("LLM 请求失败，返回默认等待指令")
    response_command = {
        "CharacterName": "Default",
        "CommandType": "Wait",
        "TargetName": "",
        "ParamID": 5,  # 等待5分钟
        "Count": 0
    }
    return jsonify(response_command), 200


if __name__ == '__main__':
    print("="*60)
    print("RimSpace LLM 服务器")
    print(f"模型: {MODEL_NAME}")
    print(f"API 地址: {OPENAI_BASE_URL}")
    print("="*60)
    print("\n服务器已启动，监听端口 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)