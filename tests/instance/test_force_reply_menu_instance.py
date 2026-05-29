from aiogram.types import ForceReply

from aiogram_dialog_manager.instance.menu import ForceReplyMenuInstance


class TestForceReplyMenuInstance:
    def test_get_markup(self):
        menu = ForceReplyMenuInstance(type_name="fr_menu", input_field_placeholder="Type here", selective=True)
        markup = menu.get_markup()
        assert isinstance(markup, ForceReply)
        assert markup.force_reply is True

    def test_get_markup_keyboard_type_ignored(self):
        menu = ForceReplyMenuInstance(type_name="fr_menu")
        markup = menu.get_markup("inline")
        assert isinstance(markup, ForceReply)


class TestForceReplyMenuInstanceSerialization:
    def test_roundtrip(self):
        menu = ForceReplyMenuInstance(type_name="fr_menu", input_field_placeholder="Type...", selective=True)
        dumped = menu.model_dump(mode="json")
        restored = ForceReplyMenuInstance.model_validate(dumped)
        assert restored.id == menu.id
        assert restored.type_name == "fr_menu"
        assert restored.input_field_placeholder == "Type..."
        assert restored.selective is True

    def test_defaults_roundtrip(self):
        menu = ForceReplyMenuInstance(type_name="fr_menu")
        dumped = menu.model_dump(mode="json")
        restored = ForceReplyMenuInstance.model_validate(dumped)
        assert restored.input_field_placeholder is None
        assert restored.selective is None
