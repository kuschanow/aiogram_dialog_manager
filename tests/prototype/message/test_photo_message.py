from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubPhoto


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestPhotoMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubPhoto()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "photo_msg"
        assert instance.text == "caption"

    async def test_do_send(self, operator, mock_bot):
        proto = StubPhoto()
        target = make_target()
        instance = make_instance("photo_msg")
        msg = await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        assert msg is not None
        mock_bot.send_photo.assert_awaited_once()

    async def test_get_input_media(self, operator):
        proto = StubPhoto()
        media = await proto.get_input_media(operator, None, parse_mode="HTML")
        assert media.media == "photo_file_id"

    async def test_get_extra_params_default(self, operator):
        proto = StubPhoto()
        extra = await proto.get_extra_params(operator, None)
        assert extra.has_spoiler is None
