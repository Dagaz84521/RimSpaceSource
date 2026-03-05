# 从 Task.json 中获取工作有关内容提供给 LLM，使用内存缓存以提高查询性能。
import json
import os
import threading
import item_provider  # 可能需要查询物品信息以构建食谱提示

# 配置 Task.json 路径（尝试多个常见位置）
_TASK_JSON_PATHS = [
    os.path.join(os.path.dirname(__file__), 'Task.json'),
    os.path.join(os.path.dirname(__file__), 'Data', 'Task.json'),
    os.path.join(os.path.dirname(__file__), '..', 'Data', 'Task.json'),
]
_TASK_JSON_PATH = None
for _p in _TASK_JSON_PATHS:
    if os.path.exists(_p):
        _TASK_JSON_PATH = _p
        break

# 缓存变量
_DATA = None
_INDEX = None  # id -> recipe 映射，便于 O(1) 查询
_MTIME = 0
_LOCK = threading.Lock()


def _load_data(force=False):
    """从磁盘加载并更新内存缓存。若文件未改变且非强制，则不会重复加载。"""
    global _DATA, _INDEX, _MTIME
    with _LOCK:
        # 找到可用的 Task.json 路径
        global _TASK_JSON_PATH
        if _TASK_JSON_PATH is None:
            for _p in _TASK_JSON_PATHS:
                if os.path.exists(_p):
                    _TASK_JSON_PATH = _p
                    break

        if _TASK_JSON_PATH is None:
            _DATA = None
            _INDEX = {}
            _MTIME = 0
            return

        try:
            mtime = os.path.getmtime(_TASK_JSON_PATH)
        except OSError:
            _DATA = None
            _INDEX = {}
            _MTIME = 0
            return

        if not force and _DATA is not None and mtime == _MTIME:
            return

        with open(_TASK_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 兼容两种数据格式：
        # 1) 列表 (Data/Task.json 中的示例是列表)
        # 2) 包含 'recipes' 字段的字典
        if isinstance(data, list):
            recipes = data
        elif isinstance(data, dict) and 'recipes' in data:
            recipes = data.get('recipes', [])
        else:
            # 无法识别的格式，尝试作为空列表处理
            recipes = []

        # 统一内部数据结构（方便其它函数使用）
        _DATA = {'recipes': recipes}
        _MTIME = mtime

        # 建立灵活的 id -> recipe 索引，支持 TaskID / id（同时以 int 和 str 存储）
        index = {}
        for recipe in recipes:
            rid = None
            for key in ('TaskID', 'TaskId', 'task_id', 'id'):
                if key in recipe:
                    rid = recipe.get(key)
                    break
            if rid is None:
                continue
            try:
                rid_int = int(rid)
            except Exception:
                rid_int = None

            if rid_int is not None:
                index[rid_int] = recipe
            index[str(rid)] = recipe
        _INDEX = index


def ensure_loaded():
    """确保缓存已加载并根据文件修改时间自动刷新。"""
    if _DATA is None:
        _load_data()
    else:
        # 尝试更新（内部会检查 mtime）
        _load_data()


def get_recipe_by_ID(recipe_id):
    """根据 ID 从内存缓存中获取食谱信息。保持与原函数签名兼容。

    使用示例：
    - 直接调用 `get_recipe_by_ID('some_id')`
    - 若外部修改了 Task.json，调用 `reload_data()` 强制重载
    """
    ensure_loaded()
    if _INDEX is None:
        return None
    # 尝试多种 lookup：int、str
    try:
        key_int = int(recipe_id)
    except Exception:
        key_int = None

    if key_int is not None and key_int in _INDEX:
        return _INDEX.get(key_int)
    return _INDEX.get(str(recipe_id))

def get_recipe_by_skill(skill):
    """根据技能名称从内存缓存中获取对应的食谱信息列表。保持与原函数签名兼容。

    使用示例：
    - 直接调用 `get_recipe_by_skill('some_skill')`
    - 若外部修改了 Task.json，调用 `reload_data()` 强制重载
    """
    ensure_loaded()
    if _DATA is None:
        return []
    recipes = _DATA.get('recipes', [])
    return [r for r in recipes if skill in r.get('RequiredSkill', [])]

def reload_data():
    """强制从磁盘重新加载数据（例如外部文件已被修改时调用）。"""
    _load_data(force=True)

def get_all_recipes():
    """返回当前缓存中所有 recipes 列表（可能为 [] 或 None）。"""
    ensure_loaded()
    if _DATA is None:
        return []
    return _DATA.get('recipes', [])

def translate_recipe_to_prompt(recipe):
    """将 recipe 对象转换为适合 LLM 输入的字符串格式。"""
    if not recipe:
        return "No recipe found."

    # 安全获取字段，兼容多种键名
    rid = recipe.get('TaskID') or recipe.get('TaskId') or recipe.get('id') or 'N/A'
    rname = item_provider.get_item_name_by_id(rid) or str(rid)
    name = recipe.get('TaskName') or recipe.get('Name') or recipe.get('task_name') or 'N/A'
    ingredients = recipe.get('Ingredients', []) or []
    ingredient_names = []
    for ing in ingredients:
        iid = ing.get('ItemID') if isinstance(ing, dict) else None
        if iid is None:
            continue
        iname = item_provider.get_item_name_by_id(iid) or str(iid)
        iname += f"(ID: {iid})"
        ingredient_names.append(iname)

    skills = recipe.get('RequiredSkill', {}) or {}
    facility = recipe.get('RequiredFacility') or recipe.get('Facility') or 'N/A'

    prompt_lines = [
        f"{name}",
        f"物品名称: {rname}({rid})",
        f"所需原料: {', '.join(ingredient_names) if ingredient_names else 'None'}",
        f"需要的技能: {', '.join(skills.keys()) if skills else 'None'}",
        f"工作地点: {facility}",
    ]

    return "\n".join(prompt_lines)

def get_all_recipes_prompt():
    """获取所有食谱的综合提示文本，适合直接输入 LLM。"""
    recipes = get_all_recipes()
    if not recipes:
        return "当前没有可用的配方数据。"
    prompt = f"当前共有 {len(recipes)} 个配方：\n"
    for recipe in recipes:
        prompt += translate_recipe_to_prompt(recipe) + "\n" + ("-" * 40) + "\n"
    return prompt


def _cli_print_by_id(id_value):
    r = get_recipe_by_ID(id_value)
    print(translate_recipe_to_prompt(r))

def _cli_print_by_skill(skill_value):
    recipes = get_recipe_by_skill(skill_value)
    for r in recipes:
        print(translate_recipe_to_prompt(r))
        print("-" * 40)


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == '--id':
        _cli_print_by_id(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == '--skill':
        _cli_print_by_skill(sys.argv[2])
    else:
        print("Usage:")
        print("  python recipe_provider.py --id <recipe_id>")
        print("  python recipe_provider.py --skill <skill_name>")