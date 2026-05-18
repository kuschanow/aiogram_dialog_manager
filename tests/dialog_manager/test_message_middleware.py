from datetime import datetime, timezone

from aiogram.types import Chat, Message

from aiogram_dialog_manager.dialog_manager import DialogManager
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
