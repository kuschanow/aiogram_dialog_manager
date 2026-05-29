from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubPoll


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestPollMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubPoll()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "poll_msg"
        assert instance.text == "Best color?"

    async def test_do_send(self, operator, mock_bot):
        proto = StubPoll()
        target = make_target()
        instance = make_instance("poll_msg")
        instance.text = "Best color?"
        await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        mock_bot.send_poll.assert_awaited_once()

    async def test_get_extra_params_default(self, operator):
        proto = StubPoll()
        extra = await proto.get_extra_params(operator, None)
        assert extra.is_anonymous is None


class TestPollExtraParamsSerialization:
    def test_defaults_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.poll import PollExtraParams
        params = PollExtraParams()
        dumped = params.model_dump(mode="json")
        restored = PollExtraParams.model_validate(dumped)
        assert restored.is_anonymous is None
        assert restored.type is None
        assert restored.close_date is None

    def test_with_values_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.poll import PollExtraParams
        params = PollExtraParams(
            is_anonymous=False,
            type="quiz",
            allows_multiple_answers=True,
            correct_option_id=0,
            explanation="Because",
            open_period=30,
            is_closed=False,
        )
        dumped = params.model_dump(mode="json")
        restored = PollExtraParams.model_validate(dumped)
        assert restored.is_anonymous is False
        assert restored.type == "quiz"
        assert restored.allows_multiple_answers is True
        assert restored.correct_option_id == 0
        assert restored.explanation == "Because"
        assert restored.open_period == 30
        assert restored.is_closed is False

    def test_close_date_as_int_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.poll import PollExtraParams
        params = PollExtraParams(close_date=9999999999)
        dumped = params.model_dump(mode="json")
        restored = PollExtraParams.model_validate(dumped)
        assert restored.close_date == 9999999999
