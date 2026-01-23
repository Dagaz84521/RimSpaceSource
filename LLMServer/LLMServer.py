from flask import Flask, request, jsonify
import json
import os
from openai import OpenAI

app = Flask(__name__)
# === 配置部分 ===
# 从环境变量或配置文件中读取 OpenAI API 密钥和其他设置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4")
openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

# ==========================================
# 1. 静态数据加载器
# ==========================================
class StaticGameData:
    def __init__(self):
        self.items_map = {} # ItemID -> ItemName
        self.recipes_list = [] # List of recipe dicts
        self.load_data()
    def load_data(self):
        # 1. 加载物品数据
        try: 
            with open('./data/Item.json', 'r', encoding='utf-8') as f:
                items_data = json.load(f)
                for item in items_data:
                    self.items_map[item['ItemID']] = item['ItemName']
            print(f"已加载 {len(self.items_map)} 个物品数据")
        except Exception as e:
            print(f"加载物品数据失败: {e}")
        # 2. 加载配方数据
        try:
            with open('./data/Task.json', 'r', encoding='utf-8') as f:
                self.recipes_list = json.load(f)
            print(f"已加载 {len(self.recipes_list)} 个配方数据")
        except Exception as e:
            print(f"加载配方数据失败: {e}")

    def get_item_name(self, item_id):
        return self.items_map.get(item_id, "未知物品")

# 游戏物品信息、配方等静态数据实例
GAME_STATIC_DATA = StaticGameData()

# ==========================================
# 2. 世界数据管理器
# ==========================================
class WorldDataManager:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.agent_name = raw_data.get("TargetAgent", "Unknown")
        self.game_time = raw_data.get("GameTime", "00:00")
        self.environment = raw_data.get("Environment", "Unknown")
        self.characters = raw_data.get("Characters", [])
        self.my_status = next((c for c in self.characters if c["Name"] == self.agent_name), {})
    
    def get_self_status(self):
        if not self.my_status:
            return "未找到自身状态信息"
        stats = self.my_status.get("CharacterStats", {})
        location = self.my_status.get("Location", "未知地点")
        state = self.my_status.get("State", "未知状态")
        skills = self.my_status.get("Skills", {})
        hunger = stats.get("Hunger", 0)
        energy = stats.get("Energy", 0)
        inventory = self.my_status.get("Inventory", [])
        inv_str = ", ".join([f"{i['name']}x{i['count']}" for i in inventory]) or "Empty"
        return (f"Name:{self.agent_name}\n"
                f"Location:{location}\n"
                f"State:{state}\n"
                f"Hunger:{hunger:.1f}/100(Lower Hunger means you need food)"
                f"Energy:{energy:.1f}/100(Lower Energy means you need rest)\n"
                f"Skills:{', '.join([f'{k}:{v}' for k,v in skills.items()])}\n"
                f"Inventory:{inv_str}\n")
    
    def search_recipes(self, keyword = ""):
        results = []
        for task in GAME_STATIC_DATA.recipes_list:
            task_name = task.get("TaskName", "")
            product_id = task.get("ProductItemID")
            product_name = GAME_STATIC_DATA.get_item_name(product_id)
            if not keyword or (keyword.lower() in task_name.lower()) or (keyword.lower() in product_name.lower()):
                # 格式化原料列表
                ingredients_str_list = []
                for ing in task.get("Ingredients", []):
                    ing_name = GAME_DATA.get_item_name(ing['ItemID'])
                    ingredients_str_list.append(f"{ing_name} x{ing['Count']}")
                ingredients_desc = ", ".join(ingredients_str_list)

                # 格式化技能要求
                skills = task.get("RequiredSkill", {})
                required_skills = [k for k, v in skills.items() if v] # 提取值为 true 的键
                skill_desc = ", ".join(required_skills) if required_skills else "None"

                # 构建返回给 LLM 的详细描述
                info = (
                    f"Recipe: {task_name} (TaskID: {task['TaskID']})\n"
                    f"  - Output: {product_name}\n" # 告诉 LLM 这到底是在造什么
                    f"  - Facility: {task['RequiredFacility']}\n"
                    f"  - Ingredients: {ingredients_desc}\n"
                    f"  - Workload: {task['TaskWorkLoad']} mins\n"
                    f"  - Required Skills: {skill_desc}"
                )
                results.append(info)
                
        if not results:
            results.append("No matching recipes found.")
        
        return "\n\n".join(results)

    def find_itmes(self, item_name):
        """工具函数：在世界容器中查找物品"""
        found = []
        for actor in self.environment:
            # 这是一个简单的查找，检查 Actor 的 Inventory
            inv = actor.get("Inventory", {}).get("items", [])
            for item in inv:
                if item_name.lower() in item.get("name", "").lower():
                    found.append(f"Found {item['count']}x {item['name']} at [{actor['ActorName']}]")
        
        if not found:
            return f"No item named '{item_name}' found in known storage."
        return "\n".join(found[:10])
# ==========================================
# 3. 定义工具Schema
# ==========================================
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_recipes",
            "description": "Search for crafting recipes. Call this when you want to make something but don't know the ingredients or facility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Name of the item to craft (e.g. 'Cotton', 'Meal'). Empty to list all."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_items",
            "description": "Find specific items in the world's storage or workstations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "The name of the item to find (e.g. 'Cotton', 'Wood')."}
                },
                "required": ["item_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finish_thinking",
            "description": "Call this ONLY when you have decided on the final action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "CommandType": {"type": "string", "enum": ["Move", "Take", "Put", "Use", "Wait"]},
                    "TargetName": {"type": "string", "description": "The target actor name (e.g. 'Stove_1', 'Storage_A')."},
                    "ParamID": {"type": "integer", "description": "ItemID for Take/Put, or TaskID/ActionID for Use."},
                    "Count": {"type": "integer", "description": "Amount of items to handle."}
                },
                "required": ["CommandType", "TargetName"]
            }
        }
    }
]

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
    raw_data = request.json
    world_mgr = WorldDataManager(raw_data)
    
    # 构建初始对话
    messages = [
        {"role": "system", "content": (
            f"You are {world_mgr.agent_name}. You are in a survival game.\n"
            f"Current Status:\n{world_mgr.get_self_status_str()}\n\n"
            "Goal:\n"
            "1. If Hunger < 30, find food (like 'Meal') and eat it.\n"
            "2. Otherwise, check available recipes and try to craft something valuable.\n"
            "3. If nothing to do, Wait.\n\n"
            "IMPORTANT: You do not know the map or recipes initially. "
            "Use tools 'search_recipes' and 'find_items' to gather info. "
            "Finally call 'finish_thinking' to act."
        )}
    ]

    final_command = None
    
    # 最多允许 5 轮思考，防止死循环
    for i in range(5):
        print(f"--- Round {i+1} Thinking ---")
        
        # 1. 调用 LLM
        response = client.chat.completions.create(
            model="gpt-4o", # 建议使用支持 Function Calling 较好的模型
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto" 
        )
        
        response_msg = response.choices[0].message
        messages.append(response_msg) # 将 LLM 的回复加入历史
        
        # 2. 检查是否有工具调用
        if response_msg.tool_calls:
            for tool_call in response_msg.tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"Tool Call: {func_name} | Args: {args}")
                
                tool_result = ""
                
                # --- 执行本地逻辑 ---
                if func_name == "search_recipes":
                    tool_result = world_mgr.search_recipes(args.get("keyword", ""))
                elif func_name == "find_items":
                    tool_result = world_mgr.find_items(args.get("item_name", ""))
                elif func_name == "finish_thinking":
                    # --- 思考结束，提取指令 ---
                    final_command = {
                        "CharacterName": world_mgr.agent_name,
                        "CommandType": args.get("CommandType"),
                        "TargetName": args.get("TargetName"),
                        "ParamID": args.get("ParamID", 0),
                        "Count": args.get("Count", 0)
                    }
                    break # 跳出工具循环
                
                print(f"Tool Result: {tool_result[:100]}...") # 打印部分结果
                
                # 3. 将工具结果反馈给 LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": tool_result
                })
            
            if final_command:
                break
        else:
            # LLM 没有调用工具，可能在闲聊，强制结束或者继续引导
            print("LLM Response without tool:", response_msg.content)
            # 如果没有得到指令，默认给个 Wait
            break

    # 兜底：如果循环结束还没结果
    if not final_command:
        print("Warning: No command generated after max rounds.")
        final_command = {
            "CharacterName": world_mgr.agent_name,
            "CommandType": "Wait",
            "TargetName": "",
            "ParamID": 5,
            "Count": 0
        }

    return jsonify(final_command), 200


if __name__ == '__main__':
    print("="*60)
    print("RimSpace LLM 服务器")
    print(f"模型: {MODEL_NAME}")
    print(f"API 地址: {OPENAI_BASE_URL}")
    print("="*60)
    print("\n服务器已启动，监听端口 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)