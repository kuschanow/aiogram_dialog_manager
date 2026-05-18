from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget, SendParams
from tests.helpers import StubDocument


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_instance(type_name="msg") -> BotMessageInstance:
    return BotMessageInstance(type_name=type_name, text="text")


class TestDocumentMessagePrototype:
    async def test_get_instance(self, operator):
        proto = StubDocument()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "doc_msg"

    async def test_do_send(self, operator, mock_bot):
        proto = StubDocument()
        target = make_target()
        instance = make_instance("doc_msg")
        await proto._do_send(mock_bot, operator, None, target, instance, SendParams(), None)
        mock_bot.send_document.assert_awaited_once()

    async def test_get_input_media(self, operator):
        proto = StubDocument()
        media = await proto.get_input_media(operator, None)
        assert media.media == "doc_file_id"

    async def test_get_extra_params_default(self, operator):
        proto = StubDocument()
        extra = await proto.get_extra_params(operator, None)
        assert extra.thumbnail is None
