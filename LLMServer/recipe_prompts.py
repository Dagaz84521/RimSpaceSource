

def get_recipe_system_prompt(task_recipes_json):
    """
    接收来自 C++ 的 TaskRecipes JSON 数据，
    返回格式化后的 System Prompt 字符串。
    """
    if not task_recipes_json:
        return ""

    prompt = "### Production Recipes (Reference Manual) ###\n"
    prompt += "Use these recipes to plan your actions. You must be at the correct workstation and have ingredients ready.\n\n"

    # 遍历 JSON 数据生成自然语言
    # 假设 C++ 传来的结构是 Key(TaskID) -> Value(Details)
    for task_id, task_data in task_recipes_json.items():
        task_name = task_data.get("TaskName", "Unknown Task")
        station = task_data.get("RequiredFacility", "Any Workbench")
        product = get_Item_From_ID(task_data.get("ProductID", "Unknown Item"))
        
        # 处理原料列表
        ingredients = task_data.get("Ingredients", [])
        ing_list = []
        for ing in ingredients:
            # 兼容 C++ 可能传来的不同字段名 (Name/ItemID, Count)
            ing_name = ing.get("Name", f"Item_{ing.get('ItemID')}")
            ing_count = ing.get("Count", 1)
            ing_list.append(f"{ing_count}x {ing_name}")
        
        inputs_str = ", ".join(ing_list)

        # 生成单条规则
        prompt += f"- To produce [{product}]:\n"
        prompt += f"  1. Go to [{station}]\n"
        prompt += f"  2. Ensure you have: {inputs_str}\n"
        prompt += f"  3. Command: WorkAt({station}, TaskID={task_id})\n\n"

    prompt += "### End of Recipes ###\n"
    return prompt

def get_common_rules_prompt():
    """
    返回通用的游戏规则 Prompt，也可以放在这里
    """
    return """
    General Rules:
    1. If you lack ingredients, search Storage first.
    2. If you are hungry (Nutrition < 30), find food and Eat.
    3. Do not stand idle if there are tasks in the queue.
    """