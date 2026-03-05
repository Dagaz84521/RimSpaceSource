# 主要用于将游戏中的状态转换为文本描述，供LLM使用
from item_provider import get_item_name_by_id
from game_state_for_test import game_state

def get_all_actor_names_prompt(environment):
    """从环境对象中提取所有场所的名称列表。"""
    if not environment:
        return []
    actors = environment.get('Actors', [])
    prompt = f"环境中共有 {len(actors)} 个场所。分别是：\n"
    for actor in actors:
        name = actor.get('ActorName') or actor.get('Name') or 'Unknown'
        prompt += f"- {name}\n"
    return prompt

def get_all_actor_names(environment):
    """从环境对象中提取所有场所的名称列表。"""
    if not environment:
        return []
    actors = environment.get('Actors', [])
    names = []
    for actor in actors:
        name = actor.get('ActorName') or actor.get('Name') or 'Unknown'
        names.append(name)
    return names

def transform_cultivate_type_to_text(cultivate_type):
    if cultivate_type == 'ECultivateType::ECT_Corn':
        return "玉米"
    elif cultivate_type == 'ECultivateType::ECT_Cotton':
        return "棉花"
    return cultivate_type  # 默认返回原值
    
def get_target_actor_state(environment, target_name):
    """根据目标场所名称，从环境对象中提取该场所的状态信息，并转换为文本描述。"""
    if not environment:
        return "环境数据不可用。"
    actors = environment.get('Actors', [])
    prompt = f"{target_name} 的状态信息如下：\n"
    for actor in actors:
        name = actor.get('ActorName') or actor.get('Name') or 'Unknown'
        if name == target_name:
            actor_type = actor.get('ActorType') or 'UnknownType'
            inventory = actor.get('Inventory', {}) or {}
            if actor_type == 'EInteractionType::EAT_CultivateChamber':
                cultivate_info = actor.get('CultivateInfo', {}) or {}
                current_phase = cultivate_info.get('CurrentPhase', '未知阶段')
                target_cultivate_type = cultivate_info.get('TargetCultivateType', '未知类型')
                current_cultivate_type = cultivate_info.get('CurrentCultivateType', '未知类型')
                if current_phase == 'ECultivatePhase::ECP_WaitingToPlant':
                    prompt += f"培养室 '{name}' 当前处于等待种植阶段，目标种植类型为 {transform_cultivate_type_to_text(target_cultivate_type)}。\n"
                elif current_phase == 'ECultivatePhase::ECP_Growing':
                    prompt += f"培养室 '{name}' 当前处于生长阶段，正在种植 {transform_cultivate_type_to_text(current_cultivate_type)}。\n"
                elif current_phase == 'ECultivatePhase::ECP_ReadyToHarvest':
                    prompt += f"培养室 '{name}' 当前处于准备收获阶段，正在收获 {transform_cultivate_type_to_text(current_cultivate_type)}。\n"
                prompt += f"培养室 '{name}' 中的物品库存：\n"
                prompt += inventory_to_prompt(inventory)
            elif actor_type == 'EInteractionType::EAT_WorkStation':
                Tasks = actor.get('TaskList', []) or []
                if Tasks:
                    prompt += f"工作台 '{name}' 中玩家发布的任务：\n"
                    for task_id, qty in Tasks.items():
                        # 尝试映射到物品名
                        name_text = get_item_name_by_id(task_id) or get_item_name_by_id(int(task_id)) if isinstance(task_id, str) and task_id.isdigit() else None
                        display = name_text or str(task_id)
                        prompt += f"- 生产{qty}个{display}(ID:{task_id})\n"
                    prompt += f"工作台 '{name}' 中的物品库存：\n"
                    prompt += inventory_to_prompt(inventory)
            elif actor_type == 'EInteractionType::EAT_Storage':
                prompt += f"仓库 '{name}' 中的物品库存：\n"
                prompt += inventory_to_prompt(inventory)
            elif actor_type == 'EInteractionType::EAT_Stove':
                prompt += f"炉灶 '{name}' 中的物品库存：\n"
                prompt += inventory_to_prompt(inventory)
            elif actor_type == 'EInteractionType::EAT_Bed':
                prompt += f"床 '{name}' 无法存储物品\n"
            elif actor_type == 'EInteractionType::EAT_Table':
                prompt += f"桌子 '{name}' 无法存储物品\n"
            return prompt
        
def inventory_to_prompt(inventory):
    """将物品库存字典转换为文本描述。"""
    if not inventory:
        return "无物品库存。"
    prompt = "物品库存：\n"
    for item_id, qty in inventory.items():
        name_text = get_item_name_by_id(item_id) or get_item_name_by_id(int(item_id)) if isinstance(item_id, str) and item_id.isdigit() else None
        display = name_text or str(item_id)
        prompt += f"- {display}: {qty}\n"
    return prompt

def get_target_type_actor_state(environment, target_type):
    """根据目标场所类型，从环境对象中提取该类型的所有场所的状态信息，并转换为文本描述。"""
    if not environment:
        return "环境数据不可用。"
    actors = environment.get('Actors', [])
    prompt = f"环境中共有 {len(actors)} 个场所，其中类型为 '{target_type}' 的有：\n"
    for actor in actors:
        name = actor.get('ActorName') or actor.get('Name') or 'Unknown'
        actor_type = actor.get('ActorType') or 'UnknownType'
        if actor_type == target_type:
            prompt += f"- {name}\n"
    return prompt

def get_environment_state_prompt(environment):
    """将整个环境对象转换为文本描述，包含所有场所的状态信息。"""
    if not environment:
        return "环境数据不可用。"
    actors = environment.get('Actors', [])
    prompt = f"当前环境中共有 {len(actors)} 个场所。它们的状态信息如下：\n"
    for actor in actors:
        name = actor.get('ActorName') or actor.get('Name') or 'Unknown'
        prompt += get_target_actor_state(environment, name) + "\n"
    return prompt

def _test_get_target_actor_state(target_actor):
    prompt = get_target_actor_state(game_state.get("Environment", {}), target_actor)
    print(f"=== get_target_actor_state 输出 for '{target_actor}' ===")
    print(prompt)

def _test_get_all_actor_names():
    prompt = get_all_actor_names(game_state.get("Environment", {}))
    print("=== get_all_actor_names 输出 ===")
    print(prompt)



if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 2:
        _test_get_target_actor_state(sys.argv[1])
    else:
        _test_get_all_actor_names()

