from typing import Dict, Any, List, Set

from . import BaseStorage


class MemoryStorage(BaseStorage):
    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]|str] = {}
        self.set_dict: Dict[str, Set[str]] = {}

    async def get_dict(self, key: str) -> Dict[str, Any] | None:
        return self.storage[key] if key in self.storage else None

    async def get_string(self, key: str) -> str | None:
        return self.storage[key] if key in self.storage else None

    async def set(self, key: str, data: Dict[str, Any]):
        self.storage[key] = data

    async def set_value_with_index(self, key: str, data: str):
        self.storage[key] = data
        if f"value_index:{data}" not in self.set_dict:
            self.set_dict[f"value_index:{data}"] = set()
        self.set_dict[f"value_index:{data}"].add(key)

    async def get_keys_by_value(self, data: str) -> List[str]:
        return list(self.set_dict[f"value_index:{data}"])

    async def remove_index(self, data: str):
        self.set_dict.pop(f"value_index:{data}")

    async def remove(self, key: str):
        self.storage.pop(key)

    async def exists(self, key: str) -> bool:
        return key in self.storage

    async def get_range_of_keys(self, match: str) -> List[str]:
        return [key for key in self.storage.keys() if match in key]
