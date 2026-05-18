import json
from unittest.mock import AsyncMock

from aiogram_dialog_manager.storage.redis import RedisStorage


class TestRedisStorage:
    def _make_redis(self):
        return AsyncMock()

    async def test_get_dict_returns_parsed_json(self):
        redis = self._make_redis()
        redis.get.return_value = json.dumps({"x": 1}).encode()
        storage = RedisStorage(redis)
        result = await storage.get_dict("key")
        assert result == {"x": 1}
        redis.get.assert_awaited_once_with("key")

    async def test_get_dict_returns_none_when_missing(self):
        redis = self._make_redis()
        redis.get.return_value = None
        storage = RedisStorage(redis)
        result = await storage.get_dict("key")
        assert result is None

    async def test_get_string(self):
        redis = self._make_redis()
        redis.get.return_value = "some_string"
        storage = RedisStorage(redis)
        result = await storage.get_string("key")
        assert result == "some_string"

    async def test_set(self):
        redis = self._make_redis()
        storage = RedisStorage(redis)
        await storage.set("key", {"a": 2})
        redis.set.assert_awaited_once_with("key", json.dumps({"a": 2}))

    async def test_set_value_with_index(self):
        redis = self._make_redis()
        storage = RedisStorage(redis)
        await storage.set_value_with_index("button:b1", "dialog_id")
        redis.set.assert_awaited_once_with("button:b1", "dialog_id")
        redis.sadd.assert_awaited_once_with("value_index:dialog_id", "button:b1")

    async def test_get_keys_by_value(self):
        redis = self._make_redis()
        redis.smembers.return_value = {"button:b1", "button:b2"}
        storage = RedisStorage(redis)
        result = await storage.get_keys_by_value("dialog_id")
        assert set(result) == {"button:b1", "button:b2"}

    async def test_remove_index(self):
        redis = self._make_redis()
        storage = RedisStorage(redis)
        await storage.remove_index("dialog_id")
        redis.delete.assert_awaited_once_with("value_index:dialog_id")

    async def test_remove(self):
        redis = self._make_redis()
        storage = RedisStorage(redis)
        await storage.remove("key")
        redis.delete.assert_awaited_once_with("key")

    async def test_exists(self):
        redis = self._make_redis()
        redis.exists.return_value = 1
        storage = RedisStorage(redis)
        result = await storage.exists("key")
        assert result == 1

    async def test_get_range_of_keys(self):
        redis = self._make_redis()

        async def fake_scan_iter(pattern):
            for k in ["dialog:1", "dialog:2"]:
                yield k

        redis.scan_iter.return_value = fake_scan_iter("*dialog*")
        storage = RedisStorage(redis)
        result = await storage.get_range_of_keys("dialog")
        assert "dialog:1" in result
        assert "dialog:2" in result
