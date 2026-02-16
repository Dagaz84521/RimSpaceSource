# agent_manager.py
from config import SYSTEM_PROMPT_TEMPLATE, THRESHOLDS
from llm_client import LLMClient
from planner import Planner
import os

class RimSpaceAgent:
    def __init__(self, name, profession, blackboard_instance):
        self.name = name
        self.profession = profession
        self.llm = LLMClient()

        #初始化规划器和动作队列
        self.blackboard = blackboard_instance
        self.planner = Planner(self.blackboard)
        self.action_queue = []
        self.feedback_buffer = ""
        
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
        # 简单逻辑：每个任务增加 20 点压力
        task_count = len(self.blackboard.get_tasks(char_data))
        self.desires["duty"] = min(100, task_count * 20)
        #print(f"[状态更新] {self.name} - Hunger: {self.desires['hunger']}, Exhaustion: {self.desires['exhaustion']}, Duty: {self.desires['duty']}")

    def generate_observation_text(self, char_data, environment_data):
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
        
        # 获取任务列表字符串 (修正：从服务器端 Blackboard 获取，而不是从请求数据中获取)
        relevant_tasks = self.blackboard.get_tasks(char_data)
        tasks = [t.description for t in relevant_tasks]
        env_text = f"\n[Task Blackboard]: {', '.join(tasks) if tasks else 'Empty'}"
        
        # Planner 反馈信息
        if self.feedback_buffer:
            env_text += f"\n[Planner Feedback]: {self.feedback_buffer}"
            self.feedback_buffer = ""  # 清空反馈缓冲区

        return status_text + env_text

    def make_decision(self, char_data, environment_data):
        """主决策循环"""
        
        # 0. 始终先更新状态 (确保每一帧的状态都是最新的，即使在执行队列中)
        self.update_state(char_data, environment_data)

        # 1. 检查并执行动作队列
        if self.action_queue:
            next_cmd = self.action_queue.pop(0)
            
            # [修正] 补全指令信息
            next_cmd["CharacterName"] = self.name
            
            # [修正] 确保后续动作也携带原始决策信息，防止前端UI显示空白
            if "Decision" not in next_cmd and hasattr(self, 'last_decision_context'):
                next_cmd["Decision"] = self.last_decision_context
            
            # [优化] 添加剩余步数信息 (可选)
            next_cmd["RemainingSteps"] = len(self.action_queue)

            print(f"[{self.name}] Executing queued action: {next_cmd.get('CommandType')} (Left: {len(self.action_queue)})")
            return next_cmd

        # 2. 构建 Prompt
        specific_profile = self.load_profile(self.profession)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            profession=self.profession,
            name=self.name,
            specific_profile=specific_profile
        )
        user_context = self.generate_observation_text(char_data, environment_data)
        
        # 3. 调用 LLM
        print(f"[{self.name}] Thinking...")
        response_str = self.llm.query(system_prompt, user_context)
        decision_json = self.llm.parse_json_response(response_str)
        
        # [修正] 安全获取 command，防止 None
        command_type = decision_json.get("command", "Wait") # 默认为 Wait
        if not isinstance(command_type, str):
            command_type = "Wait"

        # 4. 调用 Planner 进行规划
        # 将 decision_json 直接作为 params 传入
        plan_result = self.planner.generate_plan(self.name, command_type, decision_json, environment_data)
        
        if plan_result.success:
            # 规划成功
            self.action_queue = plan_result.plan
            
            # [修正] 保存当前的决策上下文，供队列中后续动作使用
            self.last_decision_context = decision_json
            
            if self.action_queue:
                first_cmd = self.action_queue.pop(0)
                first_cmd["CharacterName"] = self.name
                first_cmd["Decision"] = decision_json # 附带决策信息
                first_cmd["RemainingSteps"] = len(self.action_queue)
                return first_cmd
            else:
                # 极其罕见的情况：成功但没有动作
                return {"CharacterName": self.name, "CommandType": "Wait", "ParamID": 1, "Count": 0, "Decision": decision_json}
        else:
            # 规划失败（如资源不足，Planner已自动发布任务）
            print(f"[{self.name}] Plan Failed: {plan_result.feedback}")
            self.feedback_buffer = f"Last Action '{command_type}' Failed: {plan_result.feedback}"
            
            # 返回 Wait 并附带失败原因
            # [优化] 这里的 Decision 需要反映出失败状态
            failure_decision = decision_json.copy()
            failure_decision["reasoning"] = f"Action Failed: {plan_result.feedback}"
            
            return {
                "CharacterName": self.name, 
                "CommandType": "Wait", 
                "ParamID": 2, 
                "Count": 0,
                "Decision": failure_decision 
            }
    
    def load_profile(self, profession):
        """从文档库加载特定职业的背景故事"""
        # 构建文件路径: LLMServerNew/../文档/profile_{profession}.txt
        current_dir = os.path.dirname(__file__)  # LLMServerNew 目录
        parent_dir = os.path.dirname(current_dir)  # Source 目录
        profile_dir = os.path.join(parent_dir, "Docs")
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