from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubLocation


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestLocationMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubLocation()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "location_msg"
        assert instance.text is None

    async def test_do_send(self, operator, mock_bot):
        proto = StubLocation()
        target = make_target()
        instance = make_instance("location_msg")
        await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        mock_bot.send_location.assert_awaited_once()

    async def test_get_extra_params_default(self, operator):
        proto = StubLocation()
        extra = await proto.get_extra_params(operator, None)
        assert extra.live_period is None


class TestLocationExtraParamsSerialization:
    def test_defaults_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.location import LocationExtraParams
        params = LocationExtraParams()
        dumped = params.model_dump(mode="json")
        restored = LocationExtraParams.model_validate(dumped)
        assert restored.horizontal_accuracy is None
        assert restored.live_period is None
        assert restored.heading is None
        assert restored.proximity_alert_radius is None

    def test_with_values_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.location import LocationExtraParams
        params = LocationExtraParams(horizontal_accuracy=1.5, live_period=60, heading=180, proximity_alert_radius=100)
        dumped = params.model_dump(mode="json")
        restored = LocationExtraParams.model_validate(dumped)
        assert restored.horizontal_accuracy == 1.5
        assert restored.live_period == 60
        assert restored.heading == 180
        assert restored.proximity_alert_radius == 100
