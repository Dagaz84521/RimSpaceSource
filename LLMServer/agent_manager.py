# agent_manager.py
from config import SYSTEM_PROMPT_TEMPLATE, THRESHOLDS
from llm_client import LLMClient
import os

class RimSpaceAgent:
    def __init__(self, name, profession):
        self.name = name
        self.profession = profession
        self.llm = LLMClient()
        
        # 内部 D2A 状态 (0-100)
        self.desires = {
            "hunger": 0,
            "exhaustion": 0,
            "duty": 0
        }

    def update_state(self, char_data, environment_data):
        """
        核心步骤：将游戏数据映射为 D2A 欲望值
        """
        # 1. 映射生理欲望
        # 假设游戏里 Energy 是 100-0 (100最精神)，我们需要反转为 Exhaustion 0-100 (100最累)
        game_energy = char_data.get("Stats", {}).get("Energy", 100)
        self.desires["exhaustion"] = max(0, 100 - game_energy)
        
        # 假设游戏里 Hunger 是 0-100 (100最饱)，我们需要反转为 Hunger Desire 0-100 (100最饿)
        game_food = char_data.get("Stats", {}).get("Food", 100)
        self.desires["hunger"] = max(0, 100 - game_food)

        # 2. 映射社会欲望 (Sense of Duty)
        # 检查黑板上的任务数量
        blackboard = environment_data.get("Blackboard", [])
        # 简单逻辑：每个任务增加 20 点压力
        task_count = len(blackboard)
        self.desires["duty"] = min(100, task_count * 20)

    def generate_observation_text(self, environment_data):
        """生成给 LLM 看的自然语言描述"""
        h = self.desires["hunger"]
        e = self.desires["exhaustion"]
        d = self.desires["duty"]
        
        status_text = f"""
        [Current Desires]
        - Hunger: {h}/100 ({'CRITICAL' if h > 70 else 'Normal'})
        - Exhaustion: {e}/100 ({'Sleepy' if e > 70 else 'Fresh'})
        - Sense of Duty: {d}/100 ({'Guilty' if d > 50 else 'Relaxed'})
        """
        
        # 获取任务列表字符串
        tasks = [t.get("TaskName", "Unknown") for t in environment_data.get("Blackboard", [])]
        env_text = f"\n[Task Blackboard]: {', '.join(tasks) if tasks else 'Empty'}"
        
        # 

        return status_text + env_text

    def make_decision(self, char_data, environment_data):
        """主决策循环"""
        # 1. 更新状态
        self.update_state(char_data, environment_data)
        
        # 2. 构建 Prompt
        specific_profile = self.load_profile(self.profession)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            profession=self.profession,
            name=self.name,
            specific_profile=specific_profile
        )
        user_context = self.generate_observation_text(environment_data)
        
        # 3. 调用 LLM
        response_str = self.llm.query(system_prompt, user_context)
        decision_json = self.llm.parse_json_response(response_str)
        
        return decision_json
    
    def load_profile(self, profession):
        """从文档库加载特定职业的背景故事"""
        # 构建文件路径: LLMServerNew/../文档/profile_{profession}.txt
        current_dir = os.path.dirname(__file__)  # LLMServerNew 目录
        parent_dir = os.path.dirname(current_dir)  # Source 目录
        profile_dir = os.path.join(parent_dir, "文档")
        profile_file = os.path.join(profile_dir, f"profile_{profession.lower()}.txt")
        
        # 读取文件内容
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Profile file not found: {profile_file}")
            return f"A skilled {profession} in the RimSpace colony."
        except Exception as e:
            print(f"Error loading profile: {e}")
            return f"A skilled {profession} in the RimSpace colony."