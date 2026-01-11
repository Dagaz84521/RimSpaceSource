from flask import Flask, request, jsonify
import json
import os
from openai import OpenAI

app = Flask(__name__)

# === LLM 配置 ===
# 可以使用 OpenAI API 或兼容的本地模型（如 Ollama、vLLM 等）
# 设置环境变量或直接填入
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "ollama")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")  # 本地模型可改为如 ""
MODEL_NAME = os.environ.get("LLM_MODEL", "deepseek-r1:14b")  # 或 "llama3", "qwen2" 等

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

# === System Prompt 定义 ===
SYSTEM_PROMPT = """你是一个太空殖民地模拟游戏中的 AI 控制器，负责为角色生成行动指令。

## 可用的指令类型 (CommandType):
- **Move**: 移动到指定地点。需要指定 TargetName（目标Actor名称）
- **Take**: 从当前位置拾取物品。需要指定 ParamID（物品ID）和 Count（数量）
- **Put**: 在当前位置放下物品。需要指定 ParamID（物品ID）和 Count（数量）
- **Use**: 使用当前位置的设施进行生产。需要指定 ParamID（任务/配方的TaskID）
- **Wait**: 等待一段时间。ParamID 表示等待的分钟数

## 设施类型说明:
- **CultivateChamber (培养仓)**: 种植作物
- **Stove (灶台)**: 烹饪食物（使用 TaskID 对应的配方）
- **WorkStation (工作台)**: 制作物品（使用 TaskID 对应的配方）
- **Loom (织布机)**: 生产布料
- **SewingMachine (缝纫机)**: 生产衣物
- **Storage (仓库)**: 存储物品
- **Bed (床)**: 休息恢复精力
- **Table (桌子)**: 进食

## 物品和配方说明:
- 系统会提供 **物品数据库**，包含所有物品的 ID 和名称
- 系统会提供 **可用配方**，包含 TaskID、所需原料和产出
- **Take/Put 指令**: ParamID 使用 **物品的 ItemID**
- **Use 指令**: ParamID 使用 **配方的 TaskID**

## 角色状态说明:
- **Hunger (饱食度)**: 低于30需要进食
- **Energy (精力)**: 低于20需要休息
- **ActionState**: Idle(空闲), Moving(移动中), Working(工作中), Eating(进食中), Sleeping(睡眠中), Waiting(等待中), Thinking(思考中)

## 决策原则:
1. 优先满足角色的基本需求（饥饿、精力）
2. 避免与其他角色争抢同一设施
3. 合理规划行动路径，减少不必要的移动
4. 考虑任务的优先级和紧迫性
5. 使用配方时确保设施库存中有足够的原料

## 重要提示:
- **TargetName 必须严格使用"环境中的设施"列表中提供的名称**，不要自己编造名称！
- **ParamID 必须使用正确的 ID**：Take/Put 用物品 ItemID，Use 用配方 TaskID
- 例如：如果列表中是 "培养仓_2"，就必须使用 "培养仓_2"，而不是 "CultivateChamber2"

## 输出格式:
你必须输出一个 JSON 对象，包含以下字段：
```json
{
    "CharacterName": "角色名称",
    "CommandType": "Move|Take|Put|Use|Wait",
    "TargetName": "目标Actor名称（Move时必填，必须从环境设施列表中选择）",
    "ParamID": 0,
    "Count": 0,
    "Reasoning": "简短说明决策理由"
}
```

注意：只输出 JSON，不要有其他文字。"""


def build_game_state_prompt(data: dict) -> str:
    """将游戏状态构建为 prompt"""
    prompt_parts = []
    
    # 时间信息
    game_time = data.get("GameTime", "未知时间")
    prompt_parts.append(f"## 当前游戏时间: {game_time}")
    
    # 目标角色
    target_agent = data.get("TargetAgent", "Unknown")
    prompt_parts.append(f"\n## 需要决策的角色: {target_agent}")
    
    # === 新增：物品数据库 ===
    item_db = data.get("ItemDatabase", {})
    if item_db:
        prompt_parts.append("\n## 物品数据库 (所有可用物品):")
        prompt_parts.append(format_item_database(item_db))
    
    # === 新增：任务配方 ===
    task_recipes = data.get("TaskRecipes", {})
    if task_recipes:
        prompt_parts.append("\n## 可用配方 (Use 指令时的 ParamID 对应 TaskID):")
        prompt_parts.append(format_task_recipes(task_recipes))
    
    # 角色信息
    characters_data = data.get("Characters", {})
    characters = characters_data.get("Characters", [])
    if characters:
        prompt_parts.append("\n## 所有角色状态:")
        for char in characters:
            # 修复：使用正确的字段名 CharacterName, CharacterStats, CharacterSkills
            char_name = char.get("CharacterName", char.get("Name", "Unknown"))
            is_target = "【需要决策】" if char_name == target_agent else ""
            stats = char.get("CharacterStats", char.get("Stats", {}))
            skills = char.get("CharacterSkills", char.get("Skills", {}))
            inventory = char.get("Inventory", {})
            
            # 获取位置和状态信息
            current_location = char.get("CurrentLocation", "未知")
            action_state = char.get("ActionState", "Unknown")
            # 简化状态显示，去掉枚举前缀
            action_state_short = action_state.replace("ECharacterActionState::", "")
            
            # 格式化库存显示
            inventory_str = format_inventory(inventory)
            
            char_info = f"""
### {char_name} {is_target}
- 当前位置: {current_location}
- 行动状态: {action_state_short}
- 饱食度: {stats.get("Hunger", 0):.1f}/{stats.get("MaxHunger", 100):.1f}
- 精力: {stats.get("Energy", 0):.1f}/{stats.get("MaxEnergy", 100):.1f}
- 技能: 烹饪={skills.get("CanCook", skills.get("bCanCook", False))}, 农业={skills.get("CanFarm", skills.get("bCanFarm", False))}, 制造={skills.get("CanCraft", skills.get("bCanCraft", False))}
- 携带物品: {inventory_str}"""
            prompt_parts.append(char_info)
    
    # 环境信息
    env_data = data.get("Environment", {})
    actors = env_data.get("Actors", [])
    if actors:
        prompt_parts.append("\n## 环境中的设施 (可用于 Move 的 TargetName):")
        for actor in actors:
            # 修复：使用正确的字段名 ActorName, ActorType
            actor_name = actor.get("ActorName", actor.get("Name", "Unknown"))
            actor_type = actor.get("ActorType", actor.get("Type", "Unknown"))
            # 简化类型显示，去掉 "EInteractionType::EAT_" 前缀
            actor_type_short = actor_type.replace("EInteractionType::EAT_", "")
            inventory = actor.get("Inventory", {})
            inventory_str = format_inventory(inventory)
            
            actor_info = f"""
### {actor_name} (类型: {actor_type_short})
- 库存: {inventory_str}"""
            prompt_parts.append(actor_info)
    
    return "\n".join(prompt_parts)


def format_inventory(inventory: dict) -> str:
    """格式化库存显示"""
    if not inventory:
        return "无"
    items = inventory.get("items", [])
    if not items:
        return "空"
    # 格式化物品列表
    item_strs = []
    for item in items:
        # 兼容多种字段名格式（UE5 发送的是小写 name/count）
        item_name = item.get("name", item.get("ItemName", item.get("Name", "未知物品")))
        item_count = item.get("count", item.get("Count", item.get("Quantity", 1)))
        item_strs.append(f"{item_name}x{item_count}")
    return ", ".join(item_strs) if item_strs else "空"


def format_item_database(item_db: dict) -> str:
    """格式化物品数据库为可读文本"""
    items = item_db.get("Items", [])
    if not items:
        return "无物品数据"
    
    lines = []
    for item in items:
        item_id = item.get("ItemID", 0)
        display_name = item.get("DisplayName", "未知")
        is_food = item.get("IsFood", False)
        food_info = ""
        if is_food:
            nutrition = item.get("NutritionValue", 0)
            food_info = f" [食物, 营养值:{nutrition}]"
        lines.append(f"- ID:{item_id} {display_name}{food_info}")
    
    return "\n".join(lines)


def format_task_recipes(task_data: dict) -> str:
    """格式化任务配方为可读文本"""
    tasks = task_data.get("Tasks", [])
    if not tasks:
        return "无配方数据"
    
    lines = []
    for task in tasks:
        task_id = task.get("TaskID", 0)
        task_name = task.get("TaskName", "未知任务")
        product_name = task.get("ProductName", "未知产物")
        workload = task.get("Workload", 0)
        required_facility = task.get("RequiredFacility", "未知设施")
        
        # 格式化原料
        ingredients = task.get("Ingredients", [])
        if ingredients:
            ingredient_strs = []
            for ing in ingredients:
                ing_name = ing.get("ItemName", f"物品{ing.get('ItemID', 0)}")
                ing_count = ing.get("Count", 1)
                ingredient_strs.append(f"{ing_name}x{ing_count}")
            ingredient_text = ", ".join(ingredient_strs)
        else:
            ingredient_text = "无需原料"
        
        lines.append(f"- TaskID:{task_id} {task_name} → 产出:{product_name} | 需要:{ingredient_text} | 需要设施:{required_facility} | 耗时:{workload}分钟")
    
    return "\n".join(lines)


def query_llm(game_state_prompt: str) -> dict:
    """向 LLM 发送请求并获取指令"""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": game_state_prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}  # 强制 JSON 输出（需要模型支持）
        )
        
        content = response.choices[0].message.content
        print(f"LLM 原始响应: {content}")
        
        # 解析 JSON
        result = json.loads(content)
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return None
    except Exception as e:
        print(f"LLM 请求错误: {e}")
        return None


def validate_and_format_command(raw_command: dict, target_agent: str) -> dict:
    """验证并格式化指令，确保符合 UE5 要求的格式"""
    valid_command_types = ["None", "Move", "Take", "Put", "Use", "Wait"]
    
    command_type = raw_command.get("CommandType", "Wait")
    if command_type not in valid_command_types:
        command_type = "Wait"
    
    # 安全获取数值，处理 null/None 的情况
    param_id = raw_command.get("ParamID")
    count = raw_command.get("Count")
    
    return {
        "CharacterName": target_agent,
        "CommandType": command_type,
        "TargetName": raw_command.get("TargetName", "") or "",
        "ParamID": int(param_id) if param_id is not None else 0,
        "Count": int(count) if count is not None else 0
    }


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
    data = request.json
    target_agent = data.get("TargetAgent", "Unknown")
    
    print(f"\n{'='*20} 收到 {target_agent} 的指令请求 {'='*20}")
    print(json.dumps(data, indent=4, ensure_ascii=False))
    
    # 1. 构建游戏状态 prompt
    game_state_prompt = build_game_state_prompt(data)
    print(f"\n--- 构建的 Prompt ---\n{game_state_prompt}\n")
    
    # 2. 查询 LLM 获取决策
    llm_response = query_llm(game_state_prompt)
    
    if llm_response:
        # 打印决策理由
        reasoning = llm_response.get("Reasoning", "无")
        print(f"\n--- LLM 决策理由 ---\n{reasoning}\n")
        
        # 3. 格式化并返回指令
        response_command = validate_and_format_command(llm_response, target_agent)
    else:
        # LLM 请求失败时的后备指令
        print("LLM 请求失败，返回默认等待指令")
        response_command = {
            "CharacterName": target_agent,
            "CommandType": "Wait",
            "TargetName": "",
            "ParamID": 5,  # 等待5分钟
            "Count": 0
        }
    
    print(f"\n--- 最终返回指令 ---\n{json.dumps(response_command, indent=2, ensure_ascii=False)}\n")
    return jsonify(response_command), 200


if __name__ == '__main__':
    print("="*60)
    print("RimSpace LLM 服务器")
    print(f"模型: {MODEL_NAME}")
    print(f"API 地址: {OPENAI_BASE_URL}")
    print("="*60)
    print("\n服务器已启动，监听端口 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)