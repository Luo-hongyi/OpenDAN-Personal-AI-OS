import time
from typing import Dict, List

class NDNDataType:
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    HTML = "html"
    BLOB = "blob"

class NDNItem:
    def __init__(self, name: str, content: bytes, content_type: str = NDNDataType.BLOB, freshness_period: int = 3600):
        self.name: str = name
        self.content: bytes = content
        self.meta_info = {
            "content_type": content_type,
            "freshness_period": freshness_period,
            "timestamp": int(time.time())
        }
        self.signature: str = self._sign_data()

    def is_fresh(self) -> bool:
        current_time = int(time.time())
        elapsed_time = current_time - self.meta_info.get("timestamp", 0)
        return elapsed_time < self.meta_info.get("freshness_period", 0)
    
    def _sign_data(self) -> str:
        return ""

    def __repr__(self) -> str:
        return (f"NDNItem(name='{self.name}', "
                f"content_type='{self.meta_info['content_type']}', "
                f"signature='{self.signature[:6]}...')")
    

class NDNDataBase:
    _instance = None

    @classmethod
    def get_instance(cls) -> 'NDNDataBase':
        if cls._instance is None:
            cls._instance = NDNDataBase()
        return cls._instance

    def __init__(self):
        self.items: Dict[str, NDNItem] = {}

    def add_item(self, item: NDNItem):
        self.items[item.name] = item

    def get_item(self, name: str) -> NDNItem:
        return self.items.get(name)

    def remove_item(self, name: str):
        if name in self.items:
            del self.items[name]

    def __repr__(self) -> str:
        return f"NDNDataBase(items={list(self.items.keys())})"