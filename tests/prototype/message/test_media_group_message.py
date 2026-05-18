from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubMediaGroup


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestMediaGroupMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubMediaGroup()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "media_group_msg"

    async def test_do_send(self, operator, mock_bot):
        proto = StubMediaGroup()
        target = make_target()
        instance = make_instance("media_group_msg")
        tg_msg = await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        mock_bot.send_media_group.assert_awaited_once()
        assert tg_msg is not None
