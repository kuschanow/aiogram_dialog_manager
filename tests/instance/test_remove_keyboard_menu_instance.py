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


class TestRemoveKeyboardMenuInstanceSerialization:
    def test_roundtrip(self):
        menu = RemoveKeyboardMenuInstance(type_name="rk_menu", selective=True)
        dumped = menu.model_dump(mode="json")
        restored = RemoveKeyboardMenuInstance.model_validate(dumped)
        assert restored.id == menu.id
        assert restored.type_name == "rk_menu"
        assert restored.selective is True

    def test_defaults_roundtrip(self):
        menu = RemoveKeyboardMenuInstance(type_name="rk_menu")
        dumped = menu.model_dump(mode="json")
        restored = RemoveKeyboardMenuInstance.model_validate(dumped)
        assert restored.selective is None
