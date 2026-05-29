import pytest

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype
from tests.helpers import StubText


class TestBaseMessagePrototypeRegistry:
    def test_registration_sets_name_property(self, monkeypatch):
        monkeypatch.setattr(BaseMessagePrototype, "_registry", BaseMessagePrototype._registry.copy())

        class MyMsg(BaseMessagePrototype, type_name="unique_msg_xyz"):
            async def get_instance(self, dialog, context) -> BotMessageInstance:
                return BotMessageInstance(type_name=self.name, menu=None)

            async def _do_send(self, bot, dialog, context, target, instance, effective_params, reply_markup):
                pass

        assert MyMsg().name == "unique_msg_xyz"
        assert "unique_msg_xyz" in BaseMessagePrototype._registry

    def test_duplicate_name_raises(self, monkeypatch):
        monkeypatch.setattr(BaseMessagePrototype, "_registry", BaseMessagePrototype._registry.copy())

        class First(BaseMessagePrototype, type_name="dup_msg_xyz"):
            async def get_instance(self, dialog, context) -> BotMessageInstance:
                return BotMessageInstance(type_name=self.name, menu=None)

            async def _do_send(self, bot, dialog, context, target, instance, effective_params, reply_markup):
                pass

        with pytest.raises(ValueError, match="dup_msg_xyz"):
            class Second(BaseMessagePrototype, type_name="dup_msg_xyz"):
                async def get_instance(self, dialog, context) -> BotMessageInstance:
                    return BotMessageInstance(type_name=self.name, menu=None)

                async def _do_send(self, bot, dialog, context, target, instance, effective_params, reply_markup):
                    pass


class TestBaseMessagePrototype:
    async def test_get_menu_default_none(self, operator):
        proto = StubText()
        result = await proto.get_menu(operator, None)
        assert result is None

    async def test_get_data_default_empty(self, operator):
        proto = StubText()
        result = await proto.get_data(operator, None)
        assert result == {}

    async def test_get_send_params_default(self, operator):
        proto = StubText()
        result = await proto.get_send_params(operator, None)
        assert isinstance(result, SendParams)

    def test_str_representation(self):
        proto = StubText()
        assert "text_msg" in str(proto)


class TestTextContentSerialization:
    def test_defaults_roundtrip(self):
        from aiogram_dialog_manager.prototype.base import TextContent
        content = TextContent()
        dumped = content.model_dump(mode="json")
        restored = TextContent.model_validate(dumped)
        assert restored.text is None
        assert restored.entities is None

    def test_with_text_roundtrip(self):
        from aiogram_dialog_manager.prototype.base import TextContent
        content = TextContent(text="Hello world")
        dumped = content.model_dump(mode="json")
        restored = TextContent.model_validate(dumped)
        assert restored.text == "Hello world"
