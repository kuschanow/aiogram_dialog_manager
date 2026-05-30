from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.dialog_operator import DialogOperator
from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import MenuInstance
from aiogram_dialog_manager.instance.message import BotMessageRecord, UserMessageRecord
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubDialog


def make_manager() -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage), storage


class TestDialogManagerCrud:
    async def test_create_dialog(self, mock_bot):
        manager, storage = make_manager()
        proto = StubDialog()
        op = await manager.create_dialog(proto, user_id=1, chat_id=2, bot=mock_bot)
        assert isinstance(op, DialogOperator)
        assert await storage.exists(f"dialog:{op.dialog.id}")

    async def test_get_dialog_returns_operator(self, mock_bot):
        manager, storage = make_manager()
        proto = StubDialog()
        op = await manager.create_dialog(proto, 1, 2, mock_bot)
        loaded = await manager.get_dialog(op.dialog.id, mock_bot)
        assert loaded is not None
        assert loaded.dialog.id == op.dialog.id

    async def test_get_dialog_returns_none_when_missing(self, mock_bot):
        manager, _ = make_manager()
        result = await manager.get_dialog("nonexistent", mock_bot)
        assert result is None

    async def test_get_active_dialog_after_set(self, mock_bot):
        manager, _ = make_manager()
        proto = StubDialog()
        op = await manager.create_dialog(proto, 10, 20, mock_bot)
        await manager.set_active_dialog(op)
        active = await manager.get_active_dialog(10, 20, mock_bot)
        assert active is not None
        assert active.dialog.id == op.dialog.id

    async def test_get_active_dialog_returns_none_when_not_set(self, mock_bot):
        manager, _ = make_manager()
        result = await manager.get_active_dialog(99, 99, mock_bot)
        assert result is None

    async def test_save_indexes_buttons(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog()
        op = await manager.create_dialog(proto, 1, 2, mock_bot)

        btn = ButtonInstance(text="OK", type_name="ok")
        menu = MenuInstance(type_name="m", buttons=[[btn]])
        record = BotMessageRecord(type_name="t", menu=menu, telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        dialog_id = await storage.get_string(f"button:{btn.id}")
        assert dialog_id == op.dialog.id

    async def test_delete_removes_dialog_and_buttons(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog()
        op = await manager.create_dialog(proto, 1, 2, mock_bot)
        await manager.set_active_dialog(op)

        btn = ButtonInstance(text="OK", type_name="ok")
        menu = MenuInstance(type_name="m", buttons=[[btn]])
        record = BotMessageRecord(type_name="t", menu=menu, telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        await manager.delete(op)
        assert not await storage.exists(f"dialog:{op.dialog.id}")
        assert not await storage.exists(f"button:{btn.id}")

    async def test_delete_does_not_remove_active_if_different_dialog(self, mock_bot):
        manager, storage = make_manager()
        proto = StubDialog()
        op1 = await manager.create_dialog(proto, 1, 2, mock_bot)
        op2 = await manager.create_dialog(proto, 1, 2, mock_bot)
        await manager.set_active_dialog(op2)
        await manager.delete(op1)
        assert await storage.exists("active:1:2")


class TestMessageIndexing:
    async def test_save_indexes_bot_message_when_enabled(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog(allow_reply_lookup=True, index_bot_messages=True)
        op = await manager.create_dialog(proto, 1, 100, mock_bot)

        record = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        assert await storage.get_string(f"msg:100:{tg_message.message_id}") == op.dialog.id

    async def test_save_does_not_index_bot_message_when_lookup_disabled(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog(allow_reply_lookup=False, index_bot_messages=True)
        op = await manager.create_dialog(proto, 1, 100, mock_bot)

        record = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        assert await storage.get_string(f"msg:100:{tg_message.message_id}") is None

    async def test_save_does_not_index_bot_message_when_index_disabled(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog(allow_reply_lookup=True, index_bot_messages=False)
        op = await manager.create_dialog(proto, 1, 100, mock_bot)

        record = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        assert await storage.get_string(f"msg:100:{tg_message.message_id}") is None

    async def test_save_indexes_user_message_when_enabled(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog(allow_reply_lookup=True, index_user_messages=True)
        op = await manager.create_dialog(proto, 1, 100, mock_bot)

        op.append_user_message(tg_message)
        await manager.save(op)

        assert await storage.get_string(f"msg:100:{tg_message.message_id}") == op.dialog.id

    async def test_save_does_not_index_user_message_when_lookup_disabled(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog(allow_reply_lookup=False, index_user_messages=True)
        op = await manager.create_dialog(proto, 1, 100, mock_bot)

        op.append_user_message(tg_message)
        await manager.save(op)

        assert await storage.get_string(f"msg:100:{tg_message.message_id}") is None

    async def test_save_does_not_index_user_message_when_index_disabled(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog(allow_reply_lookup=True, index_user_messages=False)
        op = await manager.create_dialog(proto, 1, 100, mock_bot)

        op.append_user_message(tg_message)
        await manager.save(op)

        assert await storage.get_string(f"msg:100:{tg_message.message_id}") is None

    async def test_delete_removes_message_indexes(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog(allow_reply_lookup=True, index_bot_messages=True, index_user_messages=True)
        op = await manager.create_dialog(proto, 1, 100, mock_bot)

        bot_msg = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op.dialog.append_message(bot_msg)
        op.append_user_message(tg_message)
        await manager.save(op)

        await manager.delete(op)

        assert await storage.get_string(f"msg:100:{tg_message.message_id}") is None
