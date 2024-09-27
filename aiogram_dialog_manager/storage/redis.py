import json
from typing import Dict, Any, List

from . import BaseStorage
from redis.asyncio.client import Redis

class RedisStorage(BaseStorage):
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_dict(self, key: str) -> Dict[str, Any] | None:
        return json.loads(await self.redis.get(key) or "null")

    async def get_string(self, key: str) -> str | None:
        return await self.redis.get(key)

    async def set(self, key: str, data: Dict[str, Any]):
        await self.redis.set(key, json.dumps(data))

    async def set_value_with_index(self, key: str, data: str):
        await self.redis.set(key, data)
        await self.redis.sadd(f"value_index:{data}", key)

    async def remove_index(self, data: str):
        await self.redis.delete(f"value_index:{data}")

    async def get_keys_by_value(self, data: str) -> List[str]:
        return list(await self.redis.smembers(f"value_index:{data}"))

    async def remove(self, key: str):
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key)

    async def get_range_of_keys(self, match: str) -> List[str]:
        return [key async for key in await self.redis.scan_iter(f"*{match}*")]
