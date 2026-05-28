from unittest.mock import MagicMock

from aiogram.types import InlineKeyboardMarkup

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubMenu


def make_manager(**kwargs) -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage, **kwargs), storage


async def make_instance():
    return await StubMenu().get_instance(None, None)


class TestSaveStandaloneMenu:
    async def test_returns_same_instance(self):
        manager, _ = make_manager()
        instance = await make_instance()
        result = await manager.save_standalone_menu(instance)
        assert result is instance

    async def test_stores_instance_in_storage(self):
        manager, storage = make_manager()
        instance = await make_instance()
        await manager.save_standalone_menu(instance)
        assert await storage.exists(f"standalone:{instance.id}")

    async def test_indexes_buttons(self):
        manager, storage = make_manager()
        instance = await make_instance()
        await manager.save_standalone_menu(instance)
        keys = await storage.get_keys_by_value(instance.id)
        assert any(k.startswith("sbutton:") for k in keys)

    async def test_markup_from_instance(self):
        manager, _ = make_manager()
        instance = await make_instance()
        await manager.save_standalone_menu(instance)
        markup = instance.get_markup()
        assert isinstance(markup, InlineKeyboardMarkup)
        assert len(markup.inline_keyboard[0]) == 1

    async def test_with_ttl(self):
        manager, storage = make_manager(standalone_menu_ttl=600)
        instance = await make_instance()
        await manager.save_standalone_menu(instance)
        _, expire_at = storage._storage[f"standalone:{instance.id}"]
        assert expire_at is not None

    async def test_ttl_override_none(self):
        manager, storage = make_manager(standalone_menu_ttl=600)
        instance = await make_instance()
        await manager.save_standalone_menu(instance, ttl=None)
        _, expire_at = storage._storage[f"standalone:{instance.id}"]
        assert expire_at is None


class TestDeleteStandaloneMenu:
    async def test_removes_by_instance(self):
        manager, storage = make_manager()
        instance = await make_instance()
        await manager.save_standalone_menu(instance)
        await manager.delete_standalone_menu(instance)
        assert not await storage.exists(f"standalone:{instance.id}")

    async def test_removes_by_id_string(self):
        manager, storage = make_manager()
        instance = await make_instance()
        await manager.save_standalone_menu(instance)
        await manager.delete_standalone_menu(instance.id)
        assert not await storage.exists(f"standalone:{instance.id}")

    async def test_removes_button_index(self):
        manager, storage = make_manager()
        instance = await make_instance()
        await manager.save_standalone_menu(instance)
        keys_before = await storage.get_keys_by_value(instance.id)
        await manager.delete_standalone_menu(instance)
        for key in keys_before:
            assert not await storage.exists(key)


class TestCallbackMiddlewareWithStandaloneButton:
    async def test_injects_button_and_menu_for_standalone(self, mock_bot):
        manager, _ = make_manager()
        instance = await make_instance()
        await manager.save_standalone_menu(instance)
        button_id = instance.get_markup().inline_keyboard[0][0].callback_data[2:]

        captured = {}

        async def handler(callback, data):
            captured["button"] = data.get("button")
            captured["menu"] = data.get("menu")
            captured["dialog"] = data.get("dialog")

        callback = MagicMock()
        callback.data = f"b:{button_id}"
        data = {"bot": mock_bot}
        await manager._callback_middleware(handler, callback, data)

        assert captured["button"] is not None
        assert captured["menu"] is not None
        assert captured["dialog"] is None
