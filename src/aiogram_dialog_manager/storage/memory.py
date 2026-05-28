import time
from typing import Dict, Any, List, Optional, Set, Tuple

from . import BaseStorage


class MemoryStorage(BaseStorage):
    def __init__(self):
        self._storage: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._index: Dict[str, Set[str]] = {}

    def _is_alive(self, key: str) -> bool:
        if key not in self._storage:
            return False
        _, expire_at = self._storage[key]
        if expire_at is None:
            return True
        if time.monotonic() > expire_at:
            del self._storage[key]
            return False
        return True

    async def get_dict(self, key: str) -> Dict[str, Any] | None:
        if not self._is_alive(key):
            return None
        value, _ = self._storage[key]
        return value if isinstance(value, dict) else None

    async def get_string(self, key: str) -> str | None:
        if not self._is_alive(key):
            return None
        value, _ = self._storage[key]
        return value if isinstance(value, str) else None

    async def set(self, key: str, data: Any, ttl: Optional[int] = None):
        expire_at = time.monotonic() + ttl if ttl is not None else None
        self._storage[key] = (data, expire_at)

    async def set_value_with_index(self, key: str, data: str, ttl: Optional[int] = None):
        await self.set(key, data, ttl)
        index_key = f"value_index:{data}"
        if index_key not in self._index:
            self._index[index_key] = set()
        self._index[index_key].add(key)

    async def get_keys_by_value(self, data: str) -> List[str]:
        index_key = f"value_index:{data}"
        keys = list(self._index.get(index_key, set()))
        valid = [k for k in keys if self._is_alive(k)]
        if valid_set := self._index.get(index_key):
            valid_set.intersection_update(valid)
        return valid

    async def remove_index(self, data: str):
        self._index.pop(f"value_index:{data}", None)

    async def remove(self, key: str):
        self._storage.pop(key, None)

    async def exists(self, key: str) -> bool:
        return self._is_alive(key)

    async def get_range_of_keys(self, match: str) -> List[str]:
        return [key for key in list(self._storage.keys()) if match in key and self._is_alive(key)]
