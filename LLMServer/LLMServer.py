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

if __name__ == '__main__':
    # host='0.0.0.0' 允许局域网访问，port=5000 是默认端口
    print("服务器已启动，监听端口 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)