from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubVoice


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestVoiceMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubVoice()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "voice_msg"

    async def test_do_send(self, operator, mock_bot):
        proto = StubVoice()
        target = make_target()
        instance = make_instance("voice_msg")
        await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        mock_bot.send_voice.assert_awaited_once()

    async def test_get_extra_params_default(self, operator):
        proto = StubVoice()
        extra = await proto.get_extra_params(operator, None)
        assert extra.duration is None


class TestVoiceExtraParamsSerialization:
    def test_defaults_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.voice import VoiceExtraParams
        params = VoiceExtraParams()
        dumped = params.model_dump(mode="json")
        restored = VoiceExtraParams.model_validate(dumped)
        assert restored.duration is None

    def test_with_duration_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.voice import VoiceExtraParams
        params = VoiceExtraParams(duration=45)
        dumped = params.model_dump(mode="json")
        restored = VoiceExtraParams.model_validate(dumped)
        assert restored.duration == 45
