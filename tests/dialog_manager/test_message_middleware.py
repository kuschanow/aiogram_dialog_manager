from datetime import datetime, timezone

from aiogram.types import Chat, Message, User

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.instance.message import BotMessageRecord
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubDialog


def make_manager() -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage), storage


class TestMessageMiddleware:
    async def test_injects_dialog_when_active(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog()
        op = await manager.create_dialog(proto, 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        captured = {}

        async def handler(message, data):
            captured["dialog"] = data.get("dialog")
            captured["dialog_manager"] = data.get("dialog_manager")

        data = {"bot": mock_bot}
        await manager._message_middleware(handler, tg_message, data)
        assert captured["dialog"] is not None
        assert captured["dialog"].dialog.id == op.dialog.id
        assert captured["dialog_manager"] is manager

    async def test_injects_none_when_no_active_dialog(self, mock_bot, tg_message):
        manager, _ = make_manager()

        captured = {}

        async def handler(message, data):
            captured["dialog"] = data.get("dialog")

        data = {"bot": mock_bot}
        await manager._message_middleware(handler, tg_message, data)
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

        data = {"bot": mock_bot}
        await manager._message_middleware(handler, msg, data)
        assert captured["dialog"] is None

    async def test_saves_dialog_after_handler(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog()
        op = await manager.create_dialog(proto, 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(message, data):
            data["dialog"].data["new_key"] = "value"

        data = {"bot": mock_bot}
        await manager._message_middleware(handler, tg_message, data)
        loaded = await manager.get_dialog(op.dialog.id, mock_bot)
        assert loaded.data.get("new_key") == "value"

    async def test_does_not_save_if_dialog_deleted(self, mock_bot, tg_message):
        manager, storage = make_manager()
        proto = StubDialog()
        op = await manager.create_dialog(proto, 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(message, data):
            await manager.delete(data["dialog"])

        data = {"bot": mock_bot}
        await manager._message_middleware(handler, tg_message, data)
        assert not await storage.exists(f"dialog:{op.dialog.id}")

    async def test_appends_user_message_when_save_enabled(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(save_user=True), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(message, data):
            pass

        data = {"bot": mock_bot}
        await manager._message_middleware(handler, tg_message, data)
        assert data["dialog"].dialog.current_id is not None

    async def test_does_not_append_user_message_when_save_disabled(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(save_user=False), 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def handler(message, data):
            pass

        data = {"bot": mock_bot}
        await manager._message_middleware(handler, tg_message, data)
        assert data["dialog"].dialog.current_id is None

    async def test_filter_allows_message(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(save_user=True), 42, 100, mock_bot)
        await manager.set_active_dialog(op)
        manager.set_user_message_filter(op.dialog.type_name, lambda msg: True)

        async def noop(m, d): pass

        data = {"bot": mock_bot}
        await manager._message_middleware(noop, tg_message, data)
        assert data["dialog"].dialog.current_id is not None

    async def test_filter_blocks_message(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(save_user=True), 42, 100, mock_bot)
        await manager.set_active_dialog(op)
        manager.set_user_message_filter(op.dialog.type_name, lambda msg: False)

        async def noop(m, d): pass

        data = {"bot": mock_bot}
        await manager._message_middleware(noop, tg_message, data)
        assert data["dialog"].dialog.current_id is None

    async def test_filter_for_other_type_does_not_apply(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(save_user=True), 42, 100, mock_bot)
        await manager.set_active_dialog(op)
        manager.set_user_message_filter("other_dialog_type", lambda msg: False)

        async def noop(m, d): pass

        data = {"bot": mock_bot}
        await manager._message_middleware(noop, tg_message, data)
        assert data["dialog"].dialog.current_id is not None

    async def test_filter_accepts_prototype_instance(self, mock_bot, tg_message):
        manager, _ = make_manager()
        proto = StubDialog(save_user=True)
        op = await manager.create_dialog(proto, 42, 100, mock_bot)
        await manager.set_active_dialog(op)
        manager.set_user_message_filter(proto, lambda msg: False)

        async def noop(m, d): pass

        data = {"bot": mock_bot}
        await manager._message_middleware(noop, tg_message, data)
        assert data["dialog"].dialog.current_id is None


def make_reply_to(reply_to: Message, message_id: int, user_id: int) -> Message:
    return Message(
        message_id=message_id,
        date=datetime.now(timezone.utc),
        chat=Chat(id=reply_to.chat.id, type="private"),
        from_user=User(id=user_id, is_bot=False, first_name="User"),
        reply_to_message=reply_to,
    )


class TestReplyLookup:
    async def test_resolves_dialog_via_reply_to_bot_message(self, mock_bot, tg_message):
        manager, _ = make_manager()
        proto = StubDialog(allow_reply_lookup=True, index_bot_messages=True)
        op = await manager.create_dialog(proto, 42, 100, mock_bot)

        record = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        reply_msg = make_reply_to(tg_message, message_id=10, user_id=99)
        captured = {}

        async def handler(message, data):
            captured["dialog"] = data["dialog"]

        await manager._message_middleware(handler, reply_msg, {"bot": mock_bot})
        assert captured["dialog"] is not None
        assert captured["dialog"].dialog.id == op.dialog.id

    async def test_resolves_dialog_via_reply_to_user_message(self, mock_bot, tg_message):
        manager, _ = make_manager()
        proto = StubDialog(allow_reply_lookup=True, index_user_messages=True, save_user=True)
        op = await manager.create_dialog(proto, 42, 100, mock_bot)
        await manager.set_active_dialog(op)

        async def noop(m, d): pass

        await manager._message_middleware(noop, tg_message, {"bot": mock_bot})

        reply_msg = make_reply_to(tg_message, message_id=10, user_id=99)
        captured = {}

        async def handler(message, data):
            captured["dialog"] = data["dialog"]

        await manager._message_middleware(handler, reply_msg, {"bot": mock_bot})
        assert captured["dialog"] is not None
        assert captured["dialog"].dialog.id == op.dialog.id

    async def test_no_reply_lookup_when_indexing_disabled(self, mock_bot, tg_message):
        manager, _ = make_manager()
        proto = StubDialog(allow_reply_lookup=False, index_bot_messages=False)
        op = await manager.create_dialog(proto, 42, 100, mock_bot)

        record = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        reply_msg = make_reply_to(tg_message, message_id=10, user_id=99)
        captured = {}

        async def handler(message, data):
            captured["dialog"] = data["dialog"]

        await manager._message_middleware(handler, reply_msg, {"bot": mock_bot})
        assert captured["dialog"] is None

    async def test_active_dialog_takes_priority_over_reply_lookup(self, mock_bot, tg_message):
        manager, _ = make_manager()
        proto = StubDialog(allow_reply_lookup=True, index_bot_messages=True)

        op1 = await manager.create_dialog(proto, 42, 100, mock_bot)
        record = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op1.dialog.append_message(record)
        await manager.save(op1)

        op2 = await manager.create_dialog(proto, 42, 100, mock_bot)
        await manager.set_active_dialog(op2)

        owner_reply = make_reply_to(tg_message, message_id=10, user_id=42)
        captured = {}

        async def handler(message, data):
            captured["dialog"] = data["dialog"]

        await manager._message_middleware(handler, owner_reply, {"bot": mock_bot})
        assert captured["dialog"].dialog.id == op2.dialog.id

    async def test_saves_foreign_user_message_when_flag_enabled(self, mock_bot, tg_message):
        manager, _ = make_manager()
        proto = StubDialog(
            allow_reply_lookup=True,
            index_bot_messages=True,
            save_user=True,
            save_foreign_user_messages=True,
        )
        op = await manager.create_dialog(proto, 42, 100, mock_bot)

        record = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        reply_msg = make_reply_to(tg_message, message_id=10, user_id=99)
        captured = {}

        async def handler(message, data):
            captured["nodes"] = len(data["dialog"].dialog.nodes)

        await manager._message_middleware(handler, reply_msg, {"bot": mock_bot})
        assert captured["nodes"] == 2

    async def test_does_not_save_foreign_user_message_by_default(self, mock_bot, tg_message):
        manager, _ = make_manager()
        proto = StubDialog(
            allow_reply_lookup=True,
            index_bot_messages=True,
            save_user=True,
            save_foreign_user_messages=False,
        )
        op = await manager.create_dialog(proto, 42, 100, mock_bot)

        record = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        reply_msg = make_reply_to(tg_message, message_id=10, user_id=99)
        captured = {}

        async def handler(message, data):
            captured["nodes"] = len(data["dialog"].dialog.nodes)

        await manager._message_middleware(handler, reply_msg, {"bot": mock_bot})
        assert captured["nodes"] == 1

    async def test_does_not_save_foreign_user_message_when_save_user_disabled(self, mock_bot, tg_message):
        manager, _ = make_manager()
        proto = StubDialog(
            allow_reply_lookup=True,
            index_bot_messages=True,
            save_user=False,
            save_foreign_user_messages=True,
        )
        op = await manager.create_dialog(proto, 42, 100, mock_bot)

        record = BotMessageRecord(type_name="t", telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)

        reply_msg = make_reply_to(tg_message, message_id=10, user_id=99)
        captured = {}

        async def handler(message, data):
            captured["nodes"] = len(data["dialog"].dialog.nodes)

        await manager._message_middleware(handler, reply_msg, {"bot": mock_bot})
        assert captured["nodes"] == 1
