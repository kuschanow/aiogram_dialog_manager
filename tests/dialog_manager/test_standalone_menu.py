from unittest.mock import MagicMock

from aiogram.types import InlineKeyboardMarkup

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubMenu


def make_manager() -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage), storage


class TestCreateStandaloneMenu:
    async def test_returns_menu_id_and_markup(self):
        manager, _ = make_manager()
        menu_id, markup = await manager.create_standalone_menu(StubMenu())
        assert isinstance(menu_id, str) and len(menu_id) == 32
        assert isinstance(markup, InlineKeyboardMarkup)

    async def test_stores_menu_in_storage(self):
        manager, storage = make_manager()
        menu_id, _ = await manager.create_standalone_menu(StubMenu())
        assert await storage.exists(f"standalone:{menu_id}")

    async def test_indexes_buttons(self):
        manager, storage = make_manager()
        menu_id, _ = await manager.create_standalone_menu(StubMenu())
        keys = await storage.get_keys_by_value(menu_id)
        assert any(k.startswith("sbutton:") for k in keys)

    async def test_markup_contains_buttons(self):
        manager, _ = make_manager()
        _, markup = await manager.create_standalone_menu(StubMenu())
        assert len(markup.inline_keyboard) == 1
        assert len(markup.inline_keyboard[0]) == 1

    async def test_with_context(self):
        manager, _ = make_manager()
        menu_id, _ = await manager.create_standalone_menu(StubMenu(), context={"x": 1})
        assert menu_id is not None


class TestDeleteStandaloneMenu:
    async def test_removes_menu_from_storage(self):
        manager, storage = make_manager()
        menu_id, _ = await manager.create_standalone_menu(StubMenu())
        await manager.delete_standalone_menu(menu_id)
        assert not await storage.exists(f"standalone:{menu_id}")

    async def test_removes_button_index(self):
        manager, storage = make_manager()
        menu_id, _ = await manager.create_standalone_menu(StubMenu())
        keys_before = await storage.get_keys_by_value(menu_id)
        await manager.delete_standalone_menu(menu_id)
        for key in keys_before:
            assert not await storage.exists(key)


class TestCallbackMiddlewareWithStandaloneButton:
    async def test_injects_button_and_menu_for_standalone(self, mock_bot):
        manager, _ = make_manager()
        menu_id, markup = await manager.create_standalone_menu(StubMenu())
        button_id = markup.inline_keyboard[0][0].callback_data[2:]

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