from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import AdditionalReplyMenuParameters, MenuInstance


class TestMenuInstance:
    def _make_menu(self, **kwargs) -> MenuInstance:
        btn = ButtonInstance(text="OK", type_name="ok_btn")
        return MenuInstance(type_name="my_menu", buttons=[[btn]], **kwargs)

    def test_get_markup_inline_default(self):
        menu = self._make_menu()
        markup = menu.get_markup()
        assert isinstance(markup, InlineKeyboardMarkup)

    def test_get_markup_inline_explicit(self):
        menu = self._make_menu()
        markup = menu.get_markup("inline")
        assert isinstance(markup, InlineKeyboardMarkup)

    def test_get_markup_reply(self):
        menu = self._make_menu(keyboard_type="reply")
        markup = menu.get_markup("reply")
        assert isinstance(markup, ReplyKeyboardMarkup)

    def test_get_markup_reply_with_override(self):
        menu = self._make_menu(keyboard_type="inline")
        markup = menu.get_markup("reply")
        assert isinstance(markup, ReplyKeyboardMarkup)

    def test_get_markup_reply_with_additional_params(self):
        params = AdditionalReplyMenuParameters(resize_keyboard=True, one_time_keyboard=True)
        menu = self._make_menu(keyboard_type="reply", additional_reply_parameters=params)
        markup = menu.get_markup("reply")
        assert isinstance(markup, ReplyKeyboardMarkup)
        assert markup.resize_keyboard is True

    def test_get_markup_reply_without_additional_params(self):
        menu = self._make_menu(keyboard_type="reply", additional_reply_parameters=None)
        markup = menu.get_markup("reply")
        assert isinstance(markup, ReplyKeyboardMarkup)


class TestMenuSerialization:
    def _make_menu(self, **kwargs) -> MenuInstance:
        btn = ButtonInstance(text="OK", type_name="btn")
        return MenuInstance(type_name="my_menu", buttons=[[btn]], **kwargs)

    def test_additional_reply_menu_parameters_roundtrip(self):
        params = AdditionalReplyMenuParameters(resize_keyboard=True, one_time_keyboard=True, selective=True)
        dumped = params.model_dump(mode="json")
        restored = AdditionalReplyMenuParameters.model_validate(dumped)
        assert restored.resize_keyboard is True
        assert restored.one_time_keyboard is True
        assert restored.selective is True

    def test_menu_instance_roundtrip(self):
        menu = self._make_menu(keyboard_type="reply")
        dumped = menu.model_dump(mode="json")
        restored = MenuInstance.model_validate(dumped)
        assert restored.id == menu.id
        assert restored.type_name == "my_menu"
        assert restored.keyboard_type == "reply"
        assert len(restored.buttons) == 1
        assert restored.buttons[0][0].text == "OK"

    def test_menu_instance_with_reply_params_roundtrip(self):
        params = AdditionalReplyMenuParameters(resize_keyboard=True)
        menu = self._make_menu(keyboard_type="reply", additional_reply_parameters=params)
        dumped = menu.model_dump(mode="json")
        restored = MenuInstance.model_validate(dumped)
        assert restored.additional_reply_parameters.resize_keyboard is True
