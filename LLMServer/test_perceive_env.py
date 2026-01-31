import json
import os
from llm_server import perceive_environment_tasks, get_blackboard_tasks
from llm_server import Blackboard_Instance

def main():
    # 自动拼接绝对路径，兼容直接运行
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "Log", "ServerReceive", "20260130_172435", "InstructionRequest_Farmer.json")
    print(f"加载测试数据: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    environment = data["Environment"]
    # 清空黑板任务（如果有）
    # Blackboard_Instance.tasks.clear()  # 若需要清空可解注释
    perceive_environment_tasks(environment)
    Blackboard_Instance.get_tasks
    

if __name__ == "__main__":
    main()
