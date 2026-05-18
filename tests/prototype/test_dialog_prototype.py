import pytest

from aiogram_dialog_manager.instance.dialog import DialogConfig, DialogInstance
from aiogram_dialog_manager.prototype.dialog import DialogPrototype
from tests.helpers import StubDialog


class TestDialogPrototypeRegistry:
    def test_registration_sets_name_property(self, monkeypatch):
        monkeypatch.setattr(DialogPrototype, "_registry", DialogPrototype._registry.copy())

        class MyDialog(DialogPrototype, type_name="unique_dialog_xyz"):
            pass

        assert MyDialog().name == "unique_dialog_xyz"
        assert "unique_dialog_xyz" in DialogPrototype._registry

    def test_duplicate_name_raises(self, monkeypatch):
        monkeypatch.setattr(DialogPrototype, "_registry", DialogPrototype._registry.copy())

        class First(DialogPrototype, type_name="dup_dialog_xyz"):
            pass

        with pytest.raises(ValueError, match="dup_dialog_xyz"):
            class Second(DialogPrototype, type_name="dup_dialog_xyz"):
                pass


class TestDialogPrototype:
    async def test_get_instance_creates_dialog_instance(self):
        proto = StubDialog(name="my_dialog")
        instance = await proto.get_instance(user_id=1, chat_id=2)
        assert isinstance(instance, DialogInstance)
        assert instance.type_name == "my_dialog"
        assert instance.user_id == 1
        assert instance.chat_id == 2

    async def test_get_instance_with_context(self):
        proto = StubDialog()
        instance = await proto.get_instance(1, 2, context={"foo": "bar"})
        assert instance.data == {"foo": "bar"}

    async def test_get_instance_no_context(self):
        proto = StubDialog()
        instance = await proto.get_instance(1, 2, context=None)
        assert instance.data == {}

    async def test_get_config_returns_dialog_config(self):
        proto = StubDialog()
        config = await proto.get_config()
        assert isinstance(config, DialogConfig)

    async def test_get_config_base_implementation(self):
        class BareDialog(DialogPrototype):
            @property
            def name(self):
                return "bare"

        config = await BareDialog().get_config()
        assert config.save_user_message_nodes is False
        assert config.save_bot_message_nodes is True

    async def test_initial_snapshot_stored(self):
        proto = StubDialog()
        instance = await proto.get_instance(1, 2, context={"a": 1})
        assert instance.initial_snapshot_id in instance.snapshots
        assert instance.snapshots[instance.initial_snapshot_id] == {"a": 1}

    def test_str_representation(self):
        proto = StubDialog(name="dlg")
        assert "dlg" in str(proto)
