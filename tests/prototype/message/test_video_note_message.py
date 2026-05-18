from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubVideoNote


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestVideoNoteMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubVideoNote()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "video_note_msg"

    async def test_do_send(self, operator, mock_bot):
        proto = StubVideoNote()
        target = make_target()
        instance = make_instance("video_note_msg")
        await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        mock_bot.send_video_note.assert_awaited_once()

    async def test_get_extra_params_default(self, operator):
        proto = StubVideoNote()
        extra = await proto.get_extra_params(operator, None)
        assert extra.duration is None
