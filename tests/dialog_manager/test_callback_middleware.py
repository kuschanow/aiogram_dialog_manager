from unittest.mock import MagicMock

from aiogram.types import CallbackQuery

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import MenuInstance
from aiogram_dialog_manager.instance.message import BotMessageRecord
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubDialog


def make_manager() -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage), storage


def make_callback(data: str, user_id=42) -> MagicMock:
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    return cb


class TestCallbackMiddleware:
    async def _setup_dialog_with_button(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog()
        op = await manager.create_dialog(proto, 42, 100, mock_bot)
        btn = ButtonInstance(text="OK", type_name="ok")
        menu = MenuInstance(type_name="m", buttons=[[btn]])
        record = BotMessageRecord(type_name="t", menu=menu, telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)
        return manager, storage, op, btn, record

    async def test_injects_button_and_dialog(self, mock_bot, tg_message):
        manager, storage, op, btn, record = await self._setup_dialog_with_button(mock_bot, tg_message)
        cb = make_callback(f"b:{btn.id}")

        captured = {}

        async def handler(callback, data):
            captured.update(data)

        data = {"bot": mock_bot}
        await manager._callback_middleware(handler, cb, data)

        assert captured["dialog"] is not None
        assert captured["button"] is not None
        assert captured["button"].id == btn.id
        assert captured["menu"] is not None
        assert captured["message"] is not None
        assert captured["dialog_manager"] is manager

    async def test_injects_none_for_non_button_callback(self, mock_bot):
        manager, _ = make_manager()
        cb = make_callback("not_a_button")

        captured = {}

        async def handler(callback, data):
            captured.update(data)

        data = {"bot": mock_bot}
        await manager._callback_middleware(handler, cb, data)
        assert captured["dialog"] is None
        assert captured["button"] is None

    async def test_injects_none_when_button_id_not_in_storage(self, mock_bot):
        manager, _ = make_manager()
        cb = make_callback("b:unknown_button_id")

        captured = {}

        async def handler(callback, data):
            captured.update(data)

        data = {"bot": mock_bot}
        await manager._callback_middleware(handler, cb, data)
        assert captured["dialog"] is None

    async def test_injects_none_when_button_not_in_active_branch(self, mock_bot, tg_message):
        manager, storage, op, btn, record = await self._setup_dialog_with_button(mock_bot, tg_message)
        op.switch_node(None)
        await manager.save(op)

        cb = make_callback(f"b:{btn.id}")
        captured = {}

        async def handler(callback, data):
            captured.update(data)

        data = {"bot": mock_bot}
        await manager._callback_middleware(handler, cb, data)
        assert captured["dialog"] is None

    async def test_saves_dialog_after_callback_handler(self, mock_bot, tg_message):
        manager, storage, op, btn, record = await self._setup_dialog_with_button(mock_bot, tg_message)
        cb = make_callback(f"b:{btn.id}")

        async def handler(callback, data):
            data["dialog"].data["modified"] = True

        data = {"bot": mock_bot}
        await manager._callback_middleware(handler, cb, data)
        loaded = await manager.get_dialog(op.dialog.id, mock_bot)
        assert loaded.data.get("modified") is True

    async def test_does_not_save_if_dialog_deleted_in_callback(self, mock_bot, tg_message):
        manager, storage, op, btn, record = await self._setup_dialog_with_button(mock_bot, tg_message)
        cb = make_callback(f"b:{btn.id}")

        async def handler(callback, data):
            await manager.delete(data["dialog"])

        data = {"bot": mock_bot}
        await manager._callback_middleware(handler, cb, data)
        assert not await storage.exists(f"dialog:{op.dialog.id}")
