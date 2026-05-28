from unittest.mock import MagicMock, AsyncMock

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubDialog, StubMenu


def make_manager(**kwargs) -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage, **kwargs), storage


class TestTtl:
    async def test_create_dialog_uses_manager_default_ttl(self, mock_bot):
        manager, storage = make_manager(dialog_ttl=3600)
        op = await manager.create_dialog(StubDialog(), 1, 2, mock_bot)
        _, expire_at = storage._storage[f"dialog:{op.dialog.id}"]
        assert expire_at is not None

    async def test_create_dialog_ttl_override_none(self, mock_bot):
        manager, storage = make_manager(dialog_ttl=3600)
        op = await manager.create_dialog(StubDialog(), 1, 2, mock_bot, ttl=None)
        _, expire_at = storage._storage[f"dialog:{op.dialog.id}"]
        assert expire_at is None

    async def test_create_dialog_ttl_override_value(self, mock_bot):
        manager, storage = make_manager(dialog_ttl=3600)
        op = await manager.create_dialog(StubDialog(), 1, 2, mock_bot, ttl=60)
        _, expire_at = storage._storage[f"dialog:{op.dialog.id}"]
        assert expire_at is not None

    async def test_create_dialog_no_ttl_by_default(self, mock_bot):
        manager, storage = make_manager()
        op = await manager.create_dialog(StubDialog(), 1, 2, mock_bot)
        _, expire_at = storage._storage[f"dialog:{op.dialog.id}"]
        assert expire_at is None

    async def test_standalone_menu_uses_manager_default_ttl(self):
        manager, storage = make_manager(standalone_menu_ttl=600)
        instance = await StubMenu().get_instance(None, None)
        await manager.save_standalone_menu(instance)
        _, expire_at = storage._storage[f"standalone:{instance.id}"]
        assert expire_at is not None

    async def test_standalone_menu_ttl_override_none(self):
        manager, storage = make_manager(standalone_menu_ttl=600)
        instance = await StubMenu().get_instance(None, None)
        await manager.save_standalone_menu(instance, ttl=None)
        _, expire_at = storage._storage[f"standalone:{instance.id}"]
        assert expire_at is None

    async def test_active_key_refreshed_with_ttl_on_save(self, mock_bot):
        manager, storage = make_manager(dialog_ttl=3600)
        op = await manager.create_dialog(StubDialog(), 1, 2, mock_bot)
        await manager.set_active_dialog(op)  # set active first
        await manager.save(op)  # then save refreshes TTL
        _, expire_at = storage._storage["active:1:2"]
        assert expire_at is not None

    async def test_active_key_not_set_if_not_active(self, mock_bot):
        manager, storage = make_manager(dialog_ttl=3600)
        op = await manager.create_dialog(StubDialog(), 1, 2, mock_bot)
        # never set as active — active key must not exist
        assert "active:1:2" not in storage._storage


class TestCleanupOrphaned:
    async def test_removes_dialog_without_active_pointer(self, mock_bot):
        manager, storage = make_manager()
        op = await manager.create_dialog(StubDialog(), 1, 2, mock_bot)
        # never set as active → orphaned
        count = await manager.cleanup_orphaned()
        assert count == 1
        assert not await storage.exists(f"dialog:{op.dialog.id}")

    async def test_keeps_active_dialog(self, mock_bot):
        manager, storage = make_manager()
        op = await manager.create_dialog(StubDialog(), 1, 2, mock_bot)
        await manager.set_active_dialog(op)
        count = await manager.cleanup_orphaned()
        assert count == 0
        assert await storage.exists(f"dialog:{op.dialog.id}")

    async def test_removes_standalone_menu_without_buttons(self):
        manager, storage = make_manager()
        instance = await StubMenu().get_instance(None, None)
        await manager.save_standalone_menu(instance)
        keys = await storage.get_keys_by_value(instance.id)
        for key in keys:
            await storage.remove(key)
        await storage.remove_index(instance.id)
        count = await manager.cleanup_orphaned()
        assert count == 1
        assert not await storage.exists(f"standalone:{instance.id}")

    async def test_keeps_standalone_menu_with_buttons(self):
        manager, storage = make_manager()
        instance = await StubMenu().get_instance(None, None)
        await manager.save_standalone_menu(instance)
        count = await manager.cleanup_orphaned()
        assert count == 0
        assert await storage.exists(f"standalone:{instance.id}")

    async def test_returns_zero_when_nothing_to_clean(self, mock_bot):
        manager, _ = make_manager()
        count = await manager.cleanup_orphaned()
        assert count == 0

    async def test_skips_non_dict_dialog_keys(self):
        manager, storage = make_manager()
        await storage.set("dialog:garbage", "not_a_dict")
        count = await manager.cleanup_orphaned()
        assert count == 0

    async def test_removes_orphaned_dialog_buttons(self, mock_bot, tg_message):
        from aiogram_dialog_manager.instance.button import ButtonInstance
        from aiogram_dialog_manager.instance.menu import MenuInstance
        from aiogram_dialog_manager.instance.message import BotMessageRecord

        manager, storage = make_manager()
        op = await manager.create_dialog(StubDialog(), 1, 2, mock_bot)
        btn = ButtonInstance(text="X", type_name="x")
        menu = MenuInstance(type_name="m", buttons=[[btn]])
        record = BotMessageRecord(type_name="t", menu=menu, telegram_message_instance=tg_message)
        op.dialog.append_message(record)
        await manager.save(op)
        # dialog exists but is not active → orphaned
        count = await manager.cleanup_orphaned()
        assert count == 1
        assert not await storage.exists(f"button:{btn.id}")


class TestDeadButtonHandler:
    async def test_handler_called_when_button_not_found(self, mock_bot):
        manager, _ = make_manager()
        called_with = []

        async def on_dead(callback):
            called_with.append(callback)

        manager.set_dead_button_handler(on_dead)

        callback = MagicMock()
        callback.data = "b:nonexistent_button_id"
        await manager._callback_middleware(AsyncMock(), callback, {"bot": mock_bot})
        assert len(called_with) == 1

    async def test_handler_not_called_when_button_found(self, mock_bot):
        manager, _ = make_manager()
        called = []

        async def on_dead(callback):
            called.append(True)

        manager.set_dead_button_handler(on_dead)
        instance = await StubMenu().get_instance(None, None)
        await manager.save_standalone_menu(instance)
        button_id = instance.get_markup().inline_keyboard[0][0].callback_data[2:]

        callback = MagicMock()
        callback.data = f"b:{button_id}"
        await manager._callback_middleware(AsyncMock(), callback, {"bot": mock_bot})
        assert called == []

    async def test_no_handler_set_does_not_raise(self, mock_bot):
        manager, _ = make_manager()
        callback = MagicMock()
        callback.data = "b:nonexistent"
        await manager._callback_middleware(AsyncMock(), callback, {"bot": mock_bot})
