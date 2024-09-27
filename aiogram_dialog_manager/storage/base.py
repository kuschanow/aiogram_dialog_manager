from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseStorage(ABC):
    @abstractmethod
    async def get_dict(self, key: str) -> Dict[str, Any] | None:
        pass

    @abstractmethod
    async def get_string(self, key: str) -> str | None:
        pass

    @abstractmethod
    async def set(self, key: str, data: Dict[str, Any]):
        pass

    @abstractmethod
    async def set_value_with_index(self, key: str, data: str):
        pass

    @abstractmethod
    async def get_keys_by_value(self, data: str) -> List[str]:
        pass

    @abstractmethod
    async def remove_index(self, data: str):
        pass

    @abstractmethod
    async def remove(self, key: str):
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def get_range_of_keys(self, match: str) -> List[str]:
        pass