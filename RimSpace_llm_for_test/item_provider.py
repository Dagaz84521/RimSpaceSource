# 从 Data/Item.json 中获取物品信息，使用内存缓存以提高查询性能
import json
import os
import threading

_ITEM_JSON_PATH = os.path.join(os.path.dirname(__file__), 'Data', 'Item.json')

# 缓存变量
_DATA = None
_INDEX = None  # ItemID -> item dict
_MTIME = 0
_LOCK = threading.Lock()


def _load_items(force=False):
    """从磁盘加载 Item.json 并更新内存缓存。若文件未改变且非强制，则不会重复加载。"""
    global _DATA, _INDEX, _MTIME
    with _LOCK:
        try:
            mtime = os.path.getmtime(_ITEM_JSON_PATH)
        except OSError:
            _DATA = None
            _INDEX = {}
            _MTIME = 0
            return

        if not force and _DATA is not None and mtime == _MTIME:
            return

        with open(_ITEM_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        _DATA = data
        _MTIME = mtime

        index = {}
        # 数据文件是列表，每个元素包含 ItemID
        for item in data:
            try:
                key = int(item.get('ItemID'))
            except Exception:
                continue
            index[key] = item

        _INDEX = index


def ensure_loaded():
    """确保缓存已加载并根据文件修改时间自动刷新。"""
    if _DATA is None:
        _load_items()
    else:
        _load_items()


def get_item_by_ID(item_id):
    """根据 ItemID 返回完整物品字典，找不到返回 None。"""
    ensure_loaded()
    if _INDEX is None:
        return None
    try:
        key = int(item_id)
    except Exception:
        return None
    return _INDEX.get(key)


def get_item_name_by_id(item_id):
    """根据 ItemID 返回 DisplayName（或 ItemName），找不到返回 None。"""
    item = get_item_by_ID(item_id)
    if not item:
        return None
    return item.get('DisplayName') or item.get('ItemName')


def reload_items():
    """强制从磁盘重新加载 items 数据。"""
    _load_items(force=True)


def get_all_items():
    """返回当前缓存中的所有物品列表。"""
    ensure_loaded()
    if _DATA is None:
        return []
    return _DATA
