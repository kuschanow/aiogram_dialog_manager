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
