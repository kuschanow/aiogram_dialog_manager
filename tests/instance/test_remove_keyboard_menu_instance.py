from aiogram.types import ReplyKeyboardRemove

from aiogram_dialog_manager.instance.menu import RemoveKeyboardMenuInstance


class TestRemoveKeyboardMenuInstance:
    def test_get_markup(self):
        menu = RemoveKeyboardMenuInstance(type_name="rk_menu", selective=True)
        markup = menu.get_markup()
        assert isinstance(markup, ReplyKeyboardRemove)
        assert markup.remove_keyboard is True

    def test_get_markup_keyboard_type_ignored(self):
        menu = RemoveKeyboardMenuInstance(type_name="rk_menu")
        markup = menu.get_markup("reply")
        assert isinstance(markup, ReplyKeyboardRemove)
