from flask import Flask, request, jsonify
import json
import os
from openai import OpenAI

app = Flask(__name__)
# === 配置部分 ===
# 从环境变量或配置文件中读取 OpenAI API 密钥和其他设置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "99b1922f-a206-4aab-9680-048625819b76")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
MODEL_NAME = os.getenv("MODEL_NAME", "ep-20251230111027-fprsp")
MOCK_MODE = os.getenv("LLM_MOCK", "0") == "1" or OPENAI_API_KEY == "your-api-key-here"
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
        # 1. 加载物品/配方数据（相对当前文件目录）
        try:
            base_dir = os.path.dirname(__file__)
            item_path = os.path.normpath(os.path.join(base_dir, '..', 'Data', 'Item.json'))
            task_path = os.path.normpath(os.path.join(base_dir, '..', 'Data', 'Task.json'))

            with open(item_path, 'r', encoding='utf-8') as f:
                items_data = json.load(f)
                for item in items_data:
                    self.items_map[item['ItemID']] = item['ItemName']
            print(f"已加载 {len(self.items_map)} 个物品数据")
        except Exception as e:
            print(f"加载物品数据失败: {e}")
        # 2. 加载配方数据
        try:
            with open(task_path, 'r', encoding='utf-8') as f:
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
        self.environment = raw_data.get("Environment", [])
        self.characters = raw_data.get("Characters", [])
        self.my_status = next((c for c in self.characters if c["Name"] == self.agent_name), {})
    
    def get_self_status_str(self):
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
                f"Hunger:{hunger:.1f}/100(Lower Hunger means you need food)\n"
                f"Energy:{energy:.1f}/100(Lower Energy means you need rest)\n"
                f"Skills:{', '.join([f'{k}:{v}' for k,v in skills.items()])}\n"
                f"Inventory:{inv_str}\n")
    
    def search_recipes(self, keyword = ""):
        results = []
        for task in GAME_STATIC_DATA.recipes_list:
            task_name = task.get("TaskName", "")
            product_id = task.get("ProductID")
            product_name = GAME_STATIC_DATA.get_item_name(product_id)
            if not keyword or (keyword.lower() in task_name.lower()) or (keyword.lower() in product_name.lower()):
                # 格式化原料列表
                ingredients_str_list = []
                for ing in task.get("Ingredients", []):
                    ing_name = GAME_STATIC_DATA.get_item_name(ing['ItemID'])
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

    def find_items(self, item_name):
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
    
    def find_facilities(self, facility_type=""):
        """工具函数：查找环境中的设施/Actor"""
        found = []
        for actor in self.environment:
            actor_name = actor.get("ActorName", "")
            actor_type = actor.get("Type", "")
            if not facility_type or facility_type.lower() in actor_type.lower() or facility_type.lower() in actor_name.lower():
                inv = actor.get("Inventory", {}).get("items", [])
                inv_str = ", ".join([f"{it['name']}x{it['count']}" for it in inv]) or "Empty"
                found.append(f"Facility: {actor_name} (Type: {actor_type}) - Inventory: {inv_str}")
        
        if not found:
            return f"No facility matching '{facility_type}' found in the environment."
        return "\n".join(found)
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
            "description": "Find specific ITEMS (like Corn, Cotton, Meal) in containers. Do NOT use this to find facilities/workstations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "The name of the item to find (e.g. 'Cotton', 'Corn', 'Meal')."}
                },
                "required": ["item_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_facilities",
            "description": "Find FACILITIES/WORKSTATIONS (like Stove, Storage, WorkStation) in the environment. Use this to locate where to go for crafting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "facility_type": {"type": "string", "description": "The type of facility to find (e.g. 'Stove', 'Storage', 'WorkStation'). Empty to list all."}
                },
                "required": []
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
                    "Count": {"type": "integer", "description": "Amount of items to handle."},
                    "Belief": {
                        "type": "object",
                        "description": "Your current belief state to remember across requests.",
                        "properties": {
                            "Goal": {"type": "string", "description": "What is my current goal? (e.g., 'Craft a Meal')"},
                            "Completed": {"type": "string", "description": "What have I done so far? (e.g., 'Took 5 Corn from Storage_A')"},
                            "NextSteps": {"type": "string", "description": "What do I still need to do? (e.g., 'Move to Stove, Put Corn, Use recipe')"}
                        },
                        "required": ["Goal", "Completed", "NextSteps"]
                    }
                },
                "required": ["CommandType", "TargetName", "Belief"]
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
    # 当前任务目标（后续可从外部传入或动态决策）
    current_task = "Craft a Meal to keep food supplies ready."
    
    # 读取传入的信念状态
    previous_belief = raw_data.get("Belief", None)
    belief_str = ""
    if previous_belief:
        belief_str = (
            f"\n=== YOUR PREVIOUS BELIEF (from last action) ===\n"
            f"Goal: {previous_belief.get('Goal', 'Unknown')}\n"
            f"Completed: {previous_belief.get('Completed', 'Nothing yet')}\n"
            f"NextSteps: {previous_belief.get('NextSteps', 'Unknown')}\n"
            f"==============================================\n"
        )
    
    messages = [
        {"role": "system", "content": (
            f"You are {world_mgr.agent_name}. You are in a survival/crafting game.\n"
            f"Current Status:\n{world_mgr.get_self_status_str()}\n\n"
            f"=== CURRENT TASK ===\n{current_task}\n"
            f"{belief_str}\n"
            "Decision Policy:\n"
            "- If Hunger < 30: find food (e.g., 'Meal') and eat it.\n"
            "- Else: work on your CURRENT TASK following REQUIRED action order.\n\n"
            "REQUIRED Order for crafting actions (strictly one step at a time):\n"
            "1) Take: collect required ingredients from Storage.\n"
            "2) Move: go to the required facility for the recipe.\n"
            "3) Put: place required ingredients into that facility.\n"
            "4) Use: execute the recipe with the correct TaskID at the facility.\n\n"
            "IMPORTANT: When calling finish_thinking, you MUST provide a Belief object that records:\n"
            "- Goal: your current objective\n"
            "- Completed: what you just did (this action)\n"
            "- NextSteps: what remains to be done after this action\n\n"
            "Use tools to gather info, then call 'finish_thinking' with your action AND belief."
        )}
    ]

    final_command = None
    
    # 离线模拟（无 API 密钥或明确开启 LLM_MOCK），根据世界状态给出下一步
    if MOCK_MODE:
        try:
            # 选择目标配方：制作套餐 (Meal)
            target_task = next((t for t in GAME_STATIC_DATA.recipes_list if t.get('ProductID') == 2003), None)
            storage_actor = next((a for a in world_mgr.environment if a.get('ActorName') == 'Storage_A'), None)
            stove_actor = next((a for a in world_mgr.environment if a.get('ActorName') == 'Stove_1'), None)
            chef = world_mgr.my_status
            chef_loc = chef.get('Location', '')
            chef_inv = chef.get('Inventory', [])
            needed_item_id = target_task['Ingredients'][0]['ItemID'] if target_task else 1002
            needed_item_name = GAME_STATIC_DATA.get_item_name(needed_item_id)
            needed_count = target_task['Ingredients'][0]['Count'] if target_task else 5

            def inv_count(inv_list, item_name):
                for it in inv_list:
                    # 使用模糊匹配，因为数据源可能有差异
                    if it.get('name', '').lower() == item_name.lower():
                        return it.get('count', 0)
                return 0

            # 打印调试信息
            print(f"\n=== MOCK 决策调试 ===")
            print(f"目标配方: {target_task.get('TaskName') if target_task else 'None'}")
            print(f"所需物品: {needed_item_name} (ID: {needed_item_id}) x{needed_count}")
            print(f"角色位置: {chef_loc}")
            print(f"角色背包: {chef_inv}")
            print(f"背包中 {needed_item_name} 数量: {inv_count(chef_inv, needed_item_name)}")
            if stove_actor:
                stove_inv = stove_actor.get('Inventory', {}).get('items', [])
                print(f"Stove 库存: {stove_inv}")
                print(f"Stove 中 {needed_item_name} 数量: {inv_count(stove_inv, needed_item_name)}")

            # 判断 4 步中的下一步
            reason = ""
            
            # 1) 先收集原料（Take）
            if inv_count(chef_inv, needed_item_name) < needed_count:
                reason = f"背包中 {needed_item_name} 不足 ({inv_count(chef_inv, needed_item_name)}/{needed_count})，需要从 Storage 拿取"
                final_command = {
                    "CharacterName": world_mgr.agent_name,
                    "CommandType": "Take",
                    "TargetName": storage_actor['ActorName'] if storage_actor else "Storage_A",
                    "ParamID": needed_item_id,
                    "Count": needed_count,
                    "Reason": reason
                }
            # 2) 然后移动到设施（Move）
            elif chef_loc != (stove_actor['ActorName'] if stove_actor else 'Stove_1'):
                reason = f"已有足够原料，当前在 {chef_loc}，需要移动到 Stove"
                final_command = {
                    "CharacterName": world_mgr.agent_name,
                    "CommandType": "Move",
                    "TargetName": stove_actor['ActorName'] if stove_actor else "Stove_1",
                    "ParamID": 0,
                    "Count": 0,
                    "Reason": reason
                }
            # 3) 将原料放入设施（Put）
            elif inv_count(stove_actor.get('Inventory', {}).get('items', []), needed_item_name) < needed_count:
                reason = f"已到达 Stove，需要将 {needed_item_name} 放入设施"
                final_command = {
                    "CharacterName": world_mgr.agent_name,
                    "CommandType": "Put",
                    "TargetName": stove_actor['ActorName'] if stove_actor else "Stove_1",
                    "ParamID": needed_item_id,
                    "Count": needed_count,
                    "Reason": reason
                }
            # 4) 在设施执行任务（Use）
            else:
                reason = f"原料已放入 Stove，执行配方 TaskID={target_task['TaskID'] if target_task else 200}"
                final_command = {
                    "CharacterName": world_mgr.agent_name,
                    "CommandType": "Use",
                    "TargetName": stove_actor['ActorName'] if stove_actor else "Stove_1",
                    "ParamID": (target_task['TaskID'] if target_task else 200),
                    "Count": 1,
                    "Reason": reason
                }
            
            print(f"决策: {final_command['CommandType']} -> {final_command['TargetName']}")
            print(f"原因: {reason}")
            print(f"======================\n")

        except Exception as e:
            print(f"MOCK 决策失败: {e}")
            final_command = {
                "CharacterName": world_mgr.agent_name,
                "CommandType": "Wait",
                "TargetName": "",
                "ParamID": 0,
                "Count": 0
            }
        return jsonify(final_command), 200
    
    # 最多允许 5 轮思考，防止死循环
    for i in range(5):
        print(f"--- Round {i+1} Thinking ---")
        
        # 1. 调用 LLM
        response = openai_client.chat.completions.create(
            model=MODEL_NAME, # 支持 Function Calling 的模型
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
                elif func_name == "find_facilities":
                    tool_result = world_mgr.find_facilities(args.get("facility_type", ""))
                elif func_name == "finish_thinking":
                    # --- 思考结束，提取指令和信念 ---
                    belief = args.get("Belief", {})
                    final_command = {
                        "CharacterName": world_mgr.agent_name,
                        "CommandType": args.get("CommandType"),
                        "TargetName": args.get("TargetName"),
                        "ParamID": args.get("ParamID", 0),
                        "Count": args.get("Count", 0),
                        "Belief": belief
                    }
                    # 打印信念状态
                    print(f"\n=== Agent Belief ===")
                    print(f"Goal: {belief.get('Goal', 'N/A')}")
                    print(f"Completed: {belief.get('Completed', 'N/A')}")
                    print(f"NextSteps: {belief.get('NextSteps', 'N/A')}")
                    print(f"===================\n")
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
            "ParamID": 0,
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