import json
import os

# 假设本文件与Data目录同级
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "Data")
ITEM_FILE = os.path.join(DATA_DIR, "Item.json")

# 加载物品数据
with open(ITEM_FILE, 'r', encoding='utf-8') as f:
    _item_list = json.load(f)
    _item_dict = {str(item["ItemID"]): item for item in _item_list}

def get_item_field(item_id, field, default=None):
    """
    根据item_id和字段名获取字段值。
    :param item_id: int或str
    :param field: 字段名，如"ItemName"、"DisplayName"
    :param default: 未找到时返回的默认值
    """
    item = _item_dict.get(str(item_id))
    if item:
        return item.get(field, default)
    return default

def get_item_name(item_id):
    """获取物品英文名ItemName"""
    return get_item_field(item_id, "ItemName", default=str(item_id))

def get_item_display_name(item_id):
    """获取物品中文名DisplayName"""
    return get_item_field(item_id, "DisplayName", default=str(item_id))

def get_item_space_cost(item_id):
    """获取物品占用空间SpaceCost"""
    return get_item_field(item_id, "SpaceCost", default=0)

def get_item_is_food(item_id):
    """判断物品是否为食物IsFood"""
    return get_item_field(item_id, "IsFood", default=False)

def main():
    item_id = input("请输入ItemID: ").strip()
    print("ItemID:", item_id)
    print("英文名 ItemName:", get_item_name(item_id))
    print("中文名 DisplayName:", get_item_display_name(item_id))
    print("占用空间 SpaceCost:", get_item_space_cost(item_id))
    print("是否为食物 IsFood:", get_item_is_food(item_id))

if __name__ == "__main__":
    main()