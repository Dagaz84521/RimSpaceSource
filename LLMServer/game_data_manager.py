import json
import os
import config

class GameDataManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameDataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return

        # 加载静态数据
        self.items = self._load_json(config.ITEM_DATA_PATH)
        self.tasks = self._load_json(config.TASK_DATA_PATH)

        # 建立索引
        self.item_map = {str(i["ItemID"]): i for i in self.items}
        self.task_map = {str(t["TaskID"]): t for t in self.tasks}
        self.item_name_to_id = {i["ItemName"]: i["ItemID"] for i in self.items}
        
        # 反向索引：通过 ProductID 查找对应的配方(Task)
        self.product_to_recipe = {str(t["ProductID"]): t for t in self.tasks}
        
        self._initialized = True

    def _load_json(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
