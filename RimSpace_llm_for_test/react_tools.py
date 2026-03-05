import character_state_translator
import environment_translator
import recipe_provider
import item_provider


def _to_int(value):
    try:
        return int(value)
    except Exception:
        return None


def _find_recipe_by_product_id(product_id):
    recipes = recipe_provider.get_all_recipes()
    pid = _to_int(product_id)
    if pid is None:
        return None
    for recipe in recipes:
        rid = _to_int(recipe.get("ProductID"))
        if rid == pid:
            return recipe
    return None


def _get_actor_inventory(environment, actor_name):
    actors = (environment or {}).get("Actors", [])
    for actor in actors:
        name = actor.get("ActorName") or actor.get("Name")
        if name == actor_name:
            inv = actor.get("Inventory", {})
            return inv if isinstance(inv, dict) else {}
    return {}


def _get_total_item_count(environment, item_id):
    target = str(item_id)
    total = 0
    for actor in (environment or {}).get("Actors", []):
        inv = actor.get("Inventory", {})
        if not isinstance(inv, dict):
            continue
        for key, qty in inv.items():
            if str(key) == target:
                try:
                    total += int(qty)
                except Exception:
                    pass
    return total


def _tool_get_character_state(context, tool_input):
    target_agent = (tool_input or {}).get("target_agent") or context.get("character_name")
    characters_data = context.get("data", {}).get("Characters", {}).get("Characters", [])
    if not target_agent:
        return {"ok": False, "error": "missing target_agent"}
    prompt = character_state_translator.get_character_state_prompt(target_agent, characters_data)
    return {"ok": True, "observation": prompt}


def _tool_get_all_actor_names(context, tool_input):
    environment = context.get("data", {}).get("Environment", {})
    prompt = environment_translator.get_all_actor_names_prompt(environment)
    return {"ok": True, "observation": prompt}


def _tool_get_actor_state(context, tool_input):
    actor_name = (tool_input or {}).get("actor_name")
    environment = context.get("data", {}).get("Environment", {})
    if not actor_name:
        return {"ok": False, "error": "missing actor_name"}
    prompt = environment_translator.get_target_actor_state(environment, actor_name)
    if not prompt:
        return {"ok": False, "error": f"actor not found: {actor_name}"}
    return {"ok": True, "observation": prompt}


def _tool_get_actor_states(context, tool_input):
    actor_names = (tool_input or {}).get("actor_names")
    environment = context.get("data", {}).get("Environment", {})
    if not isinstance(actor_names, list) or not actor_names:
        return {"ok": False, "error": "missing actor_names(list)"}

    parts = []
    missing = []
    for actor_name in actor_names:
        prompt = environment_translator.get_target_actor_state(environment, actor_name)
        if not prompt:
            missing.append(actor_name)
            continue
        parts.append(prompt)

    result = {
        "ok": True,
        "observation": "\n\n".join(parts) if parts else "",
    }
    if missing:
        result["missing_actors"] = missing
    return result


def _tool_get_environment_state(context, tool_input):
    environment = context.get("data", {}).get("Environment", {})
    prompt = environment_translator.get_environment_state_prompt(environment)
    return {"ok": True, "observation": prompt}


def _tool_get_recipe_by_id(context, tool_input):
    recipe_id = (tool_input or {}).get("recipe_id")
    if recipe_id is None:
        return {"ok": False, "error": "missing recipe_id"}
    recipe = recipe_provider.get_recipe_by_ID(recipe_id)
    if not recipe:
        return {"ok": False, "error": f"recipe not found: {recipe_id}"}
    prompt = recipe_provider.translate_recipe_to_prompt(recipe)
    return {"ok": True, "observation": prompt}


def _tool_get_recipes_by_skill(context, tool_input):
    skill = (tool_input or {}).get("skill")
    if not skill:
        return {"ok": False, "error": "missing skill"}
    recipes = recipe_provider.get_recipe_by_skill(skill)
    if not recipes:
        return {"ok": True, "observation": f"没有找到技能 {skill} 对应的配方。"}
    lines = []
    for recipe in recipes:
        lines.append(recipe_provider.translate_recipe_to_prompt(recipe))
    return {"ok": True, "observation": "\n".join(lines)}


def _tool_analyze_production_gap(context, tool_input):
    environment = context.get("data", {}).get("Environment", {})
    target_item_id = _to_int((tool_input or {}).get("target_item_id"))
    quantity = _to_int((tool_input or {}).get("quantity")) or 1
    facility_actor = (tool_input or {}).get("facility_actor") or "WorkStation"

    if target_item_id is None:
        return {"ok": False, "error": "missing target_item_id"}

    recipe = _find_recipe_by_product_id(target_item_id)
    if not recipe:
        return {"ok": False, "error": f"recipe not found by ProductID: {target_item_id}"}

    ingredients = recipe.get("Ingredients", []) or []
    facility_inventory = _get_actor_inventory(environment, facility_actor)

    required_items = []
    missing_for_final = []
    suggested_next_actions = []

    for ingredient in ingredients:
        item_id = _to_int((ingredient or {}).get("ItemID"))
        if item_id is None:
            continue
        required_qty = quantity
        facility_qty = _to_int(facility_inventory.get(str(item_id)))
        if facility_qty is None:
            facility_qty = _to_int(facility_inventory.get(item_id)) or 0

        total_world_qty = _get_total_item_count(environment, item_id)
        shortfall = max(0, required_qty - facility_qty)

        item_name = item_provider.get_item_name_by_id(item_id)
        required_items.append({
            "item_id": item_id,
            "item_name": item_name,
            "required_qty": required_qty,
            "facility_qty": facility_qty,
            "world_total_qty": total_world_qty,
            "shortfall": shortfall,
        })

        if shortfall > 0:
            missing = {
                "item_id": item_id,
                "item_name": item_name,
                "shortfall": shortfall,
                "world_total_qty": total_world_qty,
            }
            sub_recipe = _find_recipe_by_product_id(item_id)
            if sub_recipe:
                missing["can_craft"] = True
                missing["craft_facility"] = sub_recipe.get("RequiredFacility")
                missing["craft_task_name"] = sub_recipe.get("TaskName")
                suggested_next_actions.append(
                    f"优先补齐 {item_name or item_id}，可在 {sub_recipe.get('RequiredFacility')} 执行 {sub_recipe.get('TaskName')}"
                )
            else:
                missing["can_craft"] = False
                suggested_next_actions.append(
                    f"优先从Storage等地点搬运 {item_name or item_id} 到 {facility_actor}"
                )
            missing_for_final.append(missing)

    if not missing_for_final:
        suggested_next_actions.append(
            f"{facility_actor} 原料已满足，下一步可直接 Use 生产 {target_item_id}"
        )

    observation = {
        "target_item_id": target_item_id,
        "target_task_name": recipe.get("TaskName"),
        "facility_actor": facility_actor,
        "required_items": required_items,
        "missing_for_final": missing_for_final,
        "suggested_next_actions": suggested_next_actions,
    }
    return {"ok": True, "observation": observation}


TOOL_REGISTRY = {
    "get_character_state": _tool_get_character_state,
    "get_all_actor_names": _tool_get_all_actor_names,
    "get_actor_state": _tool_get_actor_state,
    "get_actor_states": _tool_get_actor_states,
    "get_environment_state": _tool_get_environment_state,
    "get_recipe_by_id": _tool_get_recipe_by_id,
    "get_recipes_by_skill": _tool_get_recipes_by_skill,
    "analyze_production_gap": _tool_analyze_production_gap,
}


def dispatch_tool_action(action, context):
    """ReAct Tool Dispatcher。

    action 规范：
    {
      "type": "action",
      "tool": "get_actor_state",
      "input": {"actor_name": "Storage"}
    }
    """
    if not isinstance(action, dict):
        return {"ok": False, "error": "action must be a JSON object"}

    tool_name = action.get("tool")
    tool_input = action.get("input") or {}
    if tool_name not in TOOL_REGISTRY:
        return {
            "ok": False,
            "error": f"unknown tool: {tool_name}",
            "available_tools": list(TOOL_REGISTRY.keys())
        }

    try:
        return TOOL_REGISTRY[tool_name](context, tool_input)
    except Exception as e:
        return {"ok": False, "error": f"tool execution error: {e}"}


def get_react_tools_description():
    return """
    - get_character_state(input: {}) # 无输入，查看当前Agent自己的状态
    - get_all_actor_names(input: {}) # 无输入，返回当前环境中所有地点的名称列表
    - get_actor_state(input: {\"actor_name\": \"地点名\"}) # 输入地点名称，返回该地点的状态描述
    - get_actor_states(input: {\"actor_names\": [\"Storage\", \"WorkStation\"]}) # 批量查询多个地点状态，减少轮次
    - get_environment_state(input: {}) # 无输入，返回整个环境状态的描述
    - get_recipe_by_id(input: {\"recipe_id\": 3001}) # 输入配方ID，返回该配方的描述
    - get_recipes_by_skill(input: {\"skill\": \"CanCraft\"}) # 输入技能名称，返回该技能相关的配方描述列表
    - analyze_production_gap(input: {\"target_item_id\": 3001, \"quantity\": 1, \"facility_actor\": \"WorkStation\"}) # 缺料分析：返回缺什么、是否可中间制作、以及下一步建议
    """
