from unittest.mock import MagicMock

from aiogram.types import MessageReactionUpdated

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.instance.message import BotMessageRecord, UserMessageRecord
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubDialog


def make_manager() -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage), storage


def make_reaction(user_id: int = 42, chat_id: int = 100, message_id: int = 1) -> MagicMock:
    reaction = MagicMock(spec=MessageReactionUpdated)
    reaction.user = MagicMock()
    reaction.user.id = user_id
    reaction.chat = MagicMock()
    reaction.chat.id = chat_id
    reaction.message_id = message_id
    return reaction


def make_anonymous_reaction(chat_id: int = 100, message_id: int = 1) -> MagicMock:
    reaction = MagicMock(spec=MessageReactionUpdated)
    reaction.user = None
    reaction.chat = MagicMock()
    reaction.chat.id = chat_id
    reaction.message_id = message_id
    return reaction


class TestMessageReactionMiddleware:
    async def test_injects_dialog_when_active(self, mock_bot):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        captured = {}

        async def handler(reaction, data):
            captured["dialog"] = data.get("dialog")
            captured["dialog_manager"] = data.get("dialog_manager")

        await manager._message_reaction_middleware(handler, make_reaction(), {"bot": mock_bot})
        assert captured["dialog"] is not None
        assert captured["dialog"].dialog.id == op.dialog.id
        assert captured["dialog_manager"] is manager

    async def test_injects_none_when_no_active_dialog(self, mock_bot):
        manager, _ = make_manager()

        captured = {}

        async def handler(reaction, data):
            captured["dialog"] = data.get("dialog")

        await manager._message_reaction_middleware(handler, make_reaction(), {"bot": mock_bot})
        assert captured["dialog"] is None

    async def test_injects_none_when_anonymous_reaction(self, mock_bot):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        captured = {}

        async def handler(reaction, data):
            captured["dialog"] = data.get("dialog")
            captured["message_record"] = data.get("message_record")

        await manager._message_reaction_middleware(handler, make_anonymous_reaction(), {"bot": mock_bot})
        assert captured["dialog"] is None
        assert captured["message_record"] is None

    async def test_injects_message_record_for_bot_message(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        record = BotMessageRecord(type_name="text", telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.set_active_dialog(op)
        await manager.save(op)

        captured = {}

        async def handler(reaction, data):
            captured["message_record"] = data.get("message_record")

        await manager._message_reaction_middleware(
            handler, make_reaction(message_id=tg_message.message_id), {"bot": mock_bot}
        )
        assert isinstance(captured["message_record"], BotMessageRecord)
        assert captured["message_record"].telegram_message_instance.message_id == tg_message.message_id

    async def test_injects_message_record_for_user_message(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(save_user=True), 42, 100, mock_bot)
        op.append_user_message(tg_message)
        await manager.set_active_dialog(op)
        await manager.save(op)

        captured = {}

        async def handler(reaction, data):
            captured["message_record"] = data.get("message_record")

        await manager._message_reaction_middleware(
            handler, make_reaction(message_id=tg_message.message_id), {"bot": mock_bot}
        )
        assert isinstance(captured["message_record"], UserMessageRecord)

    async def test_injects_none_message_record_when_message_not_in_dialog(self, mock_bot):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        captured = {}

        async def handler(reaction, data):
            captured["message_record"] = data.get("message_record")

        await manager._message_reaction_middleware(
            handler, make_reaction(message_id=999), {"bot": mock_bot}
        )
        assert captured["message_record"] is None

    async def test_saves_dialog_after_handler(self, mock_bot):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(reaction, data):
            data["dialog"].data["reacted"] = True

        await manager._message_reaction_middleware(handler, make_reaction(), {"bot": mock_bot})
        loaded = await manager.get_dialog(op.dialog.id, mock_bot)
        assert loaded.data.get("reacted") is True

    async def test_does_not_save_if_dialog_deleted(self, mock_bot):
        manager, storage = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(reaction, data):
            await manager.delete(data["dialog"])

        await manager._message_reaction_middleware(handler, make_reaction(), {"bot": mock_bot})
        assert not await storage.exists(f"dialog:{op.dialog.id}")
