from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubText


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestTextMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubText(text="Hello!")
        instance = await proto.get_instance(operator, None)
        assert instance.text == "Hello!"
        assert instance.type_name == "text_msg"

    async def test_do_send(self, operator, mock_bot):
        proto = StubText()
        target = make_target()
        instance = make_instance("text_msg")
        msg = await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        assert msg is not None
        mock_bot.send_message.assert_awaited_once()
