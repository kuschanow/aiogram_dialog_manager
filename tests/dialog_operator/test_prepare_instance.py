from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import MenuInstance
from tests.helpers import StubText


class TestPrepareInstanceWithMenu:
    async def test_prepare_instance_with_inline_menu(self, operator):
        btn = ButtonInstance(text="OK", type_name="ok")
        menu = MenuInstance(type_name="m", buttons=[[btn]])

        class TextWithMenu(StubText):
            async def get_menu(self, dialog, context):
                return menu

        proto = TextWithMenu()
        instance, params, markup = await operator._prepare_instance(proto, None, None, "inline")
        assert isinstance(markup, InlineKeyboardMarkup)

    async def test_prepare_instance_with_reply_menu(self, operator):
        btn = ButtonInstance(text="OK", type_name="ok")
        menu = MenuInstance(type_name="m", buttons=[[btn]], keyboard_type="reply")

        class TextWithReplyMenu(StubText):
            async def get_menu(self, dialog, context):
                return menu

        proto = TextWithReplyMenu()
        instance, params, markup = await operator._prepare_instance(proto, None, None, "reply")
        assert isinstance(markup, ReplyKeyboardMarkup)

    async def test_prepare_instance_no_menu(self, operator):
        proto = StubText()
        instance, params, markup = await operator._prepare_instance(proto, None, None, None)
        assert markup is None
