class TestMemoryStorage:
    async def test_set_and_get_dict(self, memory_storage):
        await memory_storage.set("key1", {"a": 1})
        result = await memory_storage.get_dict("key1")
        assert result == {"a": 1}

    async def test_get_dict_missing(self, memory_storage):
        assert await memory_storage.get_dict("missing") is None

    async def test_set_and_get_string(self, memory_storage):
        await memory_storage.set("key2", "hello")
        result = await memory_storage.get_string("key2")
        assert result == "hello"

    async def test_get_string_missing(self, memory_storage):
        assert await memory_storage.get_string("missing") is None

    async def test_exists_true(self, memory_storage):
        await memory_storage.set("k", "v")
        assert await memory_storage.exists("k") is True

    async def test_exists_false(self, memory_storage):
        assert await memory_storage.exists("nope") is False

    async def test_remove(self, memory_storage):
        await memory_storage.set("k", "v")
        await memory_storage.remove("k")
        assert await memory_storage.exists("k") is False

    async def test_remove_missing_key_no_error(self, memory_storage):
        await memory_storage.remove("not_there")

    async def test_set_value_with_index_creates_index(self, memory_storage):
        await memory_storage.set_value_with_index("button:abc", "dialog1")
        assert await memory_storage.get_string("button:abc") == "dialog1"
        keys = await memory_storage.get_keys_by_value("dialog1")
        assert "button:abc" in keys

    async def test_set_value_with_index_multiple_keys(self, memory_storage):
        await memory_storage.set_value_with_index("button:a", "dialog1")
        await memory_storage.set_value_with_index("button:b", "dialog1")
        keys = await memory_storage.get_keys_by_value("dialog1")
        assert set(keys) == {"button:a", "button:b"}

    async def test_get_keys_by_value_empty(self, memory_storage):
        result = await memory_storage.get_keys_by_value("unknown_dialog")
        assert result == []

    async def test_remove_index(self, memory_storage):
        await memory_storage.set_value_with_index("button:x", "d1")
        await memory_storage.remove_index("d1")
        assert await memory_storage.get_keys_by_value("d1") == []

    async def test_remove_index_missing_no_error(self, memory_storage):
        await memory_storage.remove_index("nonexistent")

    async def test_get_range_of_keys(self, memory_storage):
        await memory_storage.set("dialog:aaa", "v1")
        await memory_storage.set("dialog:bbb", "v2")
        await memory_storage.set("active:1:2", "v3")
        keys = await memory_storage.get_range_of_keys("dialog:")
        assert "dialog:aaa" in keys
        assert "dialog:bbb" in keys
        assert "active:1:2" not in keys

    async def test_key_without_ttl_does_not_expire(self, memory_storage):
        await memory_storage.set("k", "v")
        assert await memory_storage.exists("k") is True

    async def test_key_with_ttl_expires(self, memory_storage):
        await memory_storage.set("k", "v", ttl=1)
        import time
        # manually push expire_at into the past
        key_val, _ = memory_storage._storage["k"]
        memory_storage._storage["k"] = (key_val, time.monotonic() - 1)
        assert await memory_storage.exists("k") is False

    async def test_expired_key_removed_from_index(self, memory_storage):
        import time
        await memory_storage.set_value_with_index("button:z", "d1", ttl=1)
        key_val, _ = memory_storage._storage["button:z"]
        memory_storage._storage["button:z"] = (key_val, time.monotonic() - 1)
        keys = await memory_storage.get_keys_by_value("d1")
        assert "button:z" not in keys

    async def test_set_with_ttl_stores_value(self, memory_storage):
        await memory_storage.set("k", {"x": 1}, ttl=3600)
        assert await memory_storage.get_dict("k") == {"x": 1}
