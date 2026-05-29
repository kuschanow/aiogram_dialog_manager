from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubAnimation


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestAnimationMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubAnimation()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "anim_msg"

    async def test_do_send(self, operator, mock_bot):
        proto = StubAnimation()
        target = make_target()
        instance = make_instance("anim_msg")
        await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        mock_bot.send_animation.assert_awaited_once()

    async def test_get_input_media(self, operator):
        proto = StubAnimation()
        media = await proto.get_input_media(operator, None)
        assert media.media == "anim_file_id"

    async def test_get_extra_params_default(self, operator):
        proto = StubAnimation()
        extra = await proto.get_extra_params(operator, None)
        assert extra.duration is None


class TestAnimationExtraParamsSerialization:
    def test_defaults_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.animation import AnimationExtraParams
        params = AnimationExtraParams()
        dumped = params.model_dump(mode="json")
        restored = AnimationExtraParams.model_validate(dumped)
        assert restored.duration is None
        assert restored.thumbnail is None

    def test_with_values_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.animation import AnimationExtraParams
        params = AnimationExtraParams(duration=10, width=640, height=480, has_spoiler=True, show_caption_above_media=False)
        dumped = params.model_dump(mode="json")
        restored = AnimationExtraParams.model_validate(dumped)
        assert restored.duration == 10
        assert restored.width == 640
        assert restored.height == 480
        assert restored.has_spoiler is True
        assert restored.show_caption_above_media is False
