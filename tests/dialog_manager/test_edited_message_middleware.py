from datetime import datetime, timezone

from aiogram.types import Chat, Message

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.instance.message import UserMessageRecord
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubDialog


def make_manager() -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage), storage


class TestEditedMessageMiddleware:
    async def test_injects_dialog_when_active(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        captured = {}

        async def handler(message, data):
            captured["dialog"] = data.get("dialog")
            captured["dialog_manager"] = data.get("dialog_manager")

        await manager._edited_message_middleware(handler, tg_message, {"bot": mock_bot})
        assert captured["dialog"] is not None
        assert captured["dialog"].dialog.id == op.dialog.id
        assert captured["dialog_manager"] is manager

    async def test_injects_none_when_no_active_dialog(self, mock_bot, tg_message):
        manager, _ = make_manager()

        captured = {}

        async def handler(message, data):
            captured["dialog"] = data.get("dialog")

        await manager._edited_message_middleware(handler, tg_message, {"bot": mock_bot})
        assert captured["dialog"] is None

    async def test_injects_none_when_no_from_user(self, mock_bot):
        manager, _ = make_manager()
        msg = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=Chat(id=100, type="private"),
        )

        captured = {}

        async def handler(message, data):
            captured["dialog"] = data.get("dialog")

        await manager._edited_message_middleware(handler, msg, {"bot": mock_bot})
        assert captured["dialog"] is None

    async def test_injects_message_record_when_user_message_saved(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(save_user=True), 42, 100, mock_bot)
        op.append_user_message(tg_message)
        await manager.set_active_dialog(op)
        await manager.save(op)

        captured = {}

        async def handler(message, data):
            captured["message_record"] = data.get("message_record")

        await manager._edited_message_middleware(handler, tg_message, {"bot": mock_bot})
        assert isinstance(captured["message_record"], UserMessageRecord)
        assert captured["message_record"].telegram_message_instance.message_id == tg_message.message_id

    async def test_injects_none_message_record_when_not_saved(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        captured = {}

        async def handler(message, data):
            captured["message_record"] = data.get("message_record")

        await manager._edited_message_middleware(handler, tg_message, {"bot": mock_bot})
        assert captured["message_record"] is None

    async def test_saves_dialog_after_handler(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(message, data):
            data["dialog"].data["edited"] = True

        await manager._edited_message_middleware(handler, tg_message, {"bot": mock_bot})
        loaded = await manager.get_dialog(op.dialog.id, mock_bot)
        assert loaded.data.get("edited") is True

    async def test_does_not_save_if_dialog_deleted(self, mock_bot, tg_message):
        manager, storage = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(message, data):
            await manager.delete(data["dialog"])

        await manager._edited_message_middleware(handler, tg_message, {"bot": mock_bot})
        assert not await storage.exists(f"dialog:{op.dialog.id}")
