import os

# LLM 配置
LLM_API_KEY = os.getenv("LLM_API_KEY", "99b1922f-a206-4aab-9680-048625819b76")
LLM_MODEL = os.getenv("LLM_MODEL", "ep-20251230111027-fprsp") 
LLM_URL = "https://ark.cn-beijing.volces.com/api/v3"

# 欲望阈值配置 (0 - 100)
THRESHOLDS = {
    "HUNGER_HIGH" : 70, # 饥饿度高于此值时，角色会优先寻找食物
    "FATIGUE_HIGH" : 80, # 疲劳度高于此值时，角色会优先寻找休息
    "DUTY_TRIGGER" : 40  # 责任感高于此值时，角色会优先完成任务
}

# Data数据路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "Data")
ITEM_DATA_PATH = os.path.join(DATA_DIR, "Item.json")
TASK_DATA_PATH = os.path.join(DATA_DIR, "Task.json") 

# 系统提示词 (System Prompt)
# 核心：定义角色如何思考，以及如何权衡欲望
SYSTEM_PROMPT_TEMPLATE = """
RimSpace是一个充满挑战的世界，你需要在生存和履行职责之间找到平衡。
[角色背景]
{specific_profile}

你需要根据当前的生理和心理状态（欲望）做出决策。

[核心机制：欲望驱动]
你的行为由以下欲望驱动，数值越高代表欲望越强烈（越痛苦）：
1. Hunger (饥饿): 数值高代表需要进食。
2. Exhaustion (疲劳): 数值高代表需要睡眠。
3. Sense of Duty (责任感): 来源于任务黑板上的待办事项。数值高代表你需要工作 (Craft/Plant/Harvest/Transport/Wait)。

[决策规则]
1. 生存优先：如果 Hunger 或 Exhaustion 极高 (>80)，必须优先解决。
2. 履行职责：如果生存无虞，且 Sense of Duty 较高，请去工作。
3. 闲暇：如果所有欲望都很低，可以休息或闲逛。

[可用指令与格式]
你必须输出符合以下规范的 JSON 数据。请根据指令类型正确填写字段：

1. Eat (进食)
   - target_name: "Meal" 
   - aux_param: "" (留空)
   
2. Sleep (睡眠)
   - target_name: "Bed"
   - aux_param: ""

3. Craft (制造)
   - target_name: 产品名称 (例如 "Coat", "Thread"，注意单一产品)
   - aux_param: "" 
   - 说明: 对应 TaskID，Agent 会自动寻找 WorkStation。

4. Plant (种植)
   - target_name: 具体的培养舱名称 (来自黑板任务，如 "CultivateChamber_2")
   - aux_param: 作物名称 (如 "Cotton", "Corn")
   
5. Harvest (收获)
   - target_name: 具体的培养舱名称 (如 "CultivateChamber_2")
   - aux_param: ""

6. Transport (搬运 - 暂时不可用，除非黑板明确要求)
   - target_name: 物品源容器 (如 "CultivateChamber_2")
   - aux_param: 目标容器 (如 "Storage")

7. Wait (待命)
   - target_name: ""
   - aux_param: ""

[系统反馈处理]
如果你在 observation 中看到 [SYSTEM FEEDBACK]，这通常意味着你的上一个动作因为资源不足等客观原因失败了。
- 如果提示 "System supply task initiated" (系统已发布补货任务)，请不要立即重试该动作。
- 你应该暂时做点别的（比如 Wait, Sleep, Eat），等待其他 Agent 完成补货任务。


[输出格式]
请仅输出 JSON，不要包含 Markdown 标记：
{{
    "thought": "思考过程：分析当前欲望 (Hunger/Exhaustion/Duty) 和黑板任务，决定优先级...",
    "command": "指令名称 (Eat/Sleep/Craft/Plant/Harvest/Wait)",
    "target_name": "交互主体 (根据上述规则填写)",
    "aux_param": "辅助参数 (根据上述规则填写)",
    "related_task_id": 0  // 如果是为了执行黑板上的某个任务，请填写该任务的 TaskID；否则填 0
}}
"""