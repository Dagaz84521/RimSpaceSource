# 用于将角色状态转换为文本描述，供LLM使用
from item_provider import get_item_name_by_id

def get_character_state(characters, character_name):
    for char in characters:
        if char.get('CharacterName') == character_name:
            return char
        
def translate_state_to_prompt(character_state):
    if not character_state:
        return "未找到角色状态信息。"
    name = character_state.get('CharacterName', 'Unknown')
    current_location = character_state.get('CurrentLocation', '未知位置')
    stats = character_state.get('CharacterStats', {}) or {}
    hunger = stats.get('Hunger', character_state.get('Hunger', '未知'))
    max_hunger = stats.get('MaxHunger', character_state.get('MaxHunger', '未知'))
    energy = stats.get('Energy', character_state.get('Energy', '未知'))
    max_energy = stats.get('MaxEnergy', character_state.get('MaxEnergy', '未知'))
    inventory = character_state.get('Inventory', {}) or {}
    def _to_float(v):
        try:
            if v is None:
                return None
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                return float(v.strip())
            return float(v)
        except Exception:
            return None

    h = _to_float(hunger)
    mh = _to_float(max_hunger)
    e = _to_float(energy)
    me = _to_float(max_energy)

    prompt = f"角色 '{name}' 的状态信息如下：\n"
    prompt += f"- 当前位置: {current_location}\n"
    if h is not None and mh and mh > 0:
        prompt += f"- 饱食度: {h/mh*100:.1f}%({int(h)}/{int(mh)})\n"
    else:
        prompt += f"- 饱食度: 未知({hunger}/{max_hunger})\n"

    if e is not None and me and me > 0:
        prompt += f"- 精力值: {e/me*100:.1f}%({int(e)}/{int(me)})\n"
    else:
        prompt += f"- 精力值: 未知({energy}/{max_energy})\n"
    if inventory:
        prompt += "- 背包物品：\n"
        items_iter = inventory.items() if isinstance(inventory, dict) else enumerate(inventory)
        for item_id, qty in items_iter:
            name_text = None
            try:
                name_text = get_item_name_by_id(item_id)
            except Exception:
                name_text = None
            if not name_text and isinstance(item_id, str) and item_id.isdigit():
                try:
                    name_text = get_item_name_by_id(int(item_id))
                except Exception:
                    name_text = None
            display = name_text or str(item_id)
            prompt += f"  - {display}: {qty}\n"
    else:
        prompt += "- 背包物品：无\n"
    
    return prompt

def get_character_state_prompt(character_name, characters):
    char_state = get_character_state(characters, character_name)
    return translate_state_to_prompt(char_state)

def test_get_character_state(character_name):
    from game_state_for_test import game_state
    characters = game_state.get('Characters', {}).get('Characters', [])
    char_state = get_character_state(characters, character_name)
    prompt = translate_state_to_prompt(char_state)
    print(prompt)

if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 2:
        test_get_character_state(sys.argv[1])
    else:
        print("Usage: python character_state_translator.py <CharacterName>")