from unittest.mock import MagicMock

from aiogram.types import ChatMemberUpdated

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubDialog


def make_manager() -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage), storage


def make_update(user_id: int = 42, chat_id: int = 100) -> MagicMock:
    update = MagicMock(spec=ChatMemberUpdated)
    update.from_user = MagicMock()
    update.from_user.id = user_id
    update.chat = MagicMock()
    update.chat.id = chat_id
    return update


class TestChatMemberUpdatedMiddleware:
    async def test_injects_dialog_when_active(self, mock_bot):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        captured = {}

        async def handler(update, data):
            captured["dialog"] = data.get("dialog")
            captured["dialog_manager"] = data.get("dialog_manager")

        await manager._chat_member_updated_middleware(handler, make_update(), {"bot": mock_bot})
        assert captured["dialog"] is not None
        assert captured["dialog"].dialog.id == op.dialog.id
        assert captured["dialog_manager"] is manager

    async def test_injects_none_when_no_active_dialog(self, mock_bot):
        manager, _ = make_manager()

        captured = {}

        async def handler(update, data):
            captured["dialog"] = data.get("dialog")

        await manager._chat_member_updated_middleware(handler, make_update(), {"bot": mock_bot})
        assert captured["dialog"] is None

    async def test_saves_dialog_after_handler(self, mock_bot):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(update, data):
            data["dialog"].data["modified"] = True

        await manager._chat_member_updated_middleware(handler, make_update(), {"bot": mock_bot})
        loaded = await manager.get_dialog(op.dialog.id, mock_bot)
        assert loaded.data.get("modified") is True

    async def test_does_not_save_if_dialog_deleted(self, mock_bot):
        manager, storage = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(update, data):
            await manager.delete(data["dialog"])

        await manager._chat_member_updated_middleware(handler, make_update(), {"bot": mock_bot})
        assert not await storage.exists(f"dialog:{op.dialog.id}")