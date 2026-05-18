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
