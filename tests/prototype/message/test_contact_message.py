from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubContact


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestContactMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubContact()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "contact_msg"

    async def test_do_send(self, operator, mock_bot):
        proto = StubContact()
        target = make_target()
        instance = make_instance("contact_msg")
        await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        mock_bot.send_contact.assert_awaited_once()

    async def test_get_extra_params_default(self, operator):
        proto = StubContact()
        extra = await proto.get_extra_params(operator, None)
        assert extra.last_name is None


class TestContactExtraParamsSerialization:
    def test_defaults_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.contact import ContactExtraParams
        params = ContactExtraParams()
        dumped = params.model_dump(mode="json")
        restored = ContactExtraParams.model_validate(dumped)
        assert restored.last_name is None
        assert restored.vcard is None

    def test_with_values_roundtrip(self):
        from aiogram_dialog_manager.prototype.message.contact import ContactExtraParams
        params = ContactExtraParams(last_name="Doe", vcard="BEGIN:VCARD")
        dumped = params.model_dump(mode="json")
        restored = ContactExtraParams.model_validate(dumped)
        assert restored.last_name == "Doe"
        assert restored.vcard == "BEGIN:VCARD"
