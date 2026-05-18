from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubAudio


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestAudioMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubAudio()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "audio_msg"

    async def test_do_send(self, operator, mock_bot):
        proto = StubAudio()
        target = make_target()
        instance = make_instance("audio_msg")
        await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        mock_bot.send_audio.assert_awaited_once()

    async def test_get_input_media(self, operator):
        proto = StubAudio()
        media = await proto.get_input_media(operator, None)
        assert media.media == "audio_file_id"

    async def test_get_extra_params_default(self, operator):
        proto = StubAudio()
        extra = await proto.get_extra_params(operator, None)
        assert extra.duration is None
