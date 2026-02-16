import json
import os
import time
import requests # 需要 pip install requests
import sys

# 服务器地址 (确保 llm_server.py 正在运行)
SERVER_URL = "http://127.0.0.1:5000/GetInstruction"

def load_json_file(file_path):
    """加载并解析 JSON 文件"""
    # 处理路径中的引号（防止直接拖入文件路径时带引号）
    file_path = file_path.strip('"').strip("'")
    
    if not os.path.exists(file_path):
        print(f"[错误] 文件不存在: {file_path}")
        return None
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[错误] JSON 解析失败: {e}")
        return None

def send_request_to_llm(data):
    """向 LLM Server 发送 POST 请求"""
    headers = {'Content-Type': 'application/json'}
    
    print(f"\n[发送中] 目标 Agent: {data.get('TargetAgent', 'Unknown')}")
    print(f"[发送中] 正在请求 {SERVER_URL} ...")
    
    start_time = time.time()
    try:
        response = requests.post(SERVER_URL, json=data, headers=headers)
        response.raise_for_status() # 检查 HTTP 错误
        
        duration = time.time() - start_time
        result = response.json()
        
        return result, duration
        
    except requests.exceptions.ConnectionError:
        print(f"[失败] 无法连接到服务器。请确认 llm_server.py 是否已启动？")
        return None, 0
    except Exception as e:
        print(f"[失败] 请求出错: {e}")
        if 'response' in locals():
            print(f"服务器返回: {response.text}")
        return None, 0

def print_decision(decision, duration):
    """美化打印决策结果"""
    print("-" * 50)
    print(f"✅ 决策成功 (耗时: {duration:.2f}s)")
    print("-" * 50)
    
    char_name = decision.get("CharacterName", "Unknown")
    cmd_type = decision.get("CommandType", "Unknown")
    
    print(f"角色: {char_name}")
    print(f"指令: {cmd_type}")
    
    if cmd_type in ["Move", "Interact", "Plant", "Harvest"]:
        print(f"目标: {decision.get('TargetName', 'None')}")
    elif cmd_type in ["Take", "Put", "Use"]:
        print(f"参数: ID={decision.get('ParamID')}, Count={decision.get('Count')}")
    elif cmd_type == "Wait":
        print(f"等待: {decision.get('ParamID')} 分钟")
        
    # 打印原始决策理由 (如果有)
    raw_decision = decision.get("Decision", {})
    if raw_decision:
        print(f"\n[LLM 思考]:\n{raw_decision.get('thought', 'No thought recorded')}")
        if "reasoning" in raw_decision:
             print(f"[失败/调试信息]: {raw_decision.get('reasoning')}")

    # 打印后续队列长度
    steps = decision.get("RemainingSteps", 0)
    if steps > 0:
        print(f"\n[后续动作]: 队列中还有 {steps} 个动作等待执行")

    print("=" * 50)

def main():
    print("=" * 60)
    print("  LLM Server 交互测试客户端")
    print("  功能：模拟 Unreal Engine 发送请求，测试 Agent 决策")
    print("  注意：请先运行 'python llm_server.py'")
    print("=" * 60)

    while True:
        user_input = input("\n请输入测试 JSON 文件的路径 (输入 'exit' 退出): ").strip()
        
        if user_input.lower() in ['exit', 'quit']:
            print("退出测试。")
            break
            
        if not user_input:
            continue
            
        # 1. 加载数据
        request_data = load_json_file(user_input)
        if not request_data:
            continue
            
        # 2. 发送请求
        decision, duration = send_request_to_llm(request_data)
        
        # 3. 显示结果
        if decision:
            print_decision(decision, duration)

if __name__ == "__main__":
    main()