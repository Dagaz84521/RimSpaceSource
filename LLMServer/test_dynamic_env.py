import json
import os
import time
from llm_server import perceive_environment_tasks, Blackboard_Instance

def load_json_file(file_path):
    """加载JSON文件"""
    try:
        # 去除引号（如果用户直接拖拽文件路径可能会带引号）
        file_path = file_path.strip('"').strip("'")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[错误] 加载JSON失败: {e}")
        return None

def main():
    print("=" * 60)
    print("  动态环境测试脚本 (输入 'exit' 退出)")
    print("  功能：轮询输入JSON路径 -> 模拟更新 environment -> 黑板任务变更")
    print("=" * 60)

    while True:
        json_path = input("\n请输入测试JSON文件的路径 (或 'exit' 退出): ").strip()
        if json_path.lower() == 'exit':
            break
        
        if not json_path:
            continue

        data = load_json_file(json_path)
        if not data:
            continue

        environment = data.get("Environment", {})
        if not environment:
            print("[警告] JSON中没有 'Environment' 字段")
            continue

        print(f"\n[处理] 正在处理: {os.path.basename(json_path)}")

        # 1. 更新黑板任务（移除已完成的任务）
        # 注意：Blackboard.update 需要当前最新的 game_state（这里我们用整个 data 模拟）
        # 实际情况中 update 需要包含 Environment 数据的完整状态
        print("[黑板] 检查任务完成情况...")
        Blackboard_Instance.update(data)

        # 2. 感知环境生成新任务
        print("[感知] 扫描环境生成新任务...")
        perceive_environment_tasks(environment)
        # perceive_environment_tasks 直接向 Blackboard_Instance 添加任务，不需要返回值处理

        # 3. 打印当前黑板状态
        current_tasks = Blackboard_Instance.tasks
        print(f"\n[黑板状态] 当前任务数: {len(current_tasks)}")
        if not current_tasks:
            print("  (无任务)")
        else:
            for i, task in enumerate(current_tasks):
                # 兼容 BlackboardTask 对象或字典
                desc = task.description if hasattr(task, 'description') else task.get('description', 'No Desc')
                print(f"  Task #{i+1}: {desc}")
                #如果是对象，打印Goal详情
                if hasattr(task, 'goal'):
                     print(f"      Goal: {task.goal.GoalDescription()}")

if __name__ == "__main__":
    main()
