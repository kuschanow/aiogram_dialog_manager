from aiogram_dialog_manager.dialog_operator import DialogOperator
from aiogram_dialog_manager.instance.message import BotMessageRecord, MessageTarget, SendParams
from tests.helpers import StubDialog, StubText


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


class TestSendMessage:
    async def test_send_message(self, operator, mock_bot):
        proto = StubText()
        target = make_target()
        record = await operator.send_message(proto, target)
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_message.assert_awaited_once()

    async def test_send_message_with_send_params(self, operator, mock_bot):
        proto = StubText()
        target = make_target()
        params = SendParams(disable_notification=True)
        record = await operator.send_message(proto, target, send_params=params)
        assert isinstance(record, BotMessageRecord)

    async def test_send_message_with_context(self, operator, mock_bot):
        proto = StubText()
        target = make_target()
        record = await operator.send_message(proto, target, context={"key": "val"})
        assert isinstance(record, BotMessageRecord)

    async def test_send_message_with_keyboard_type(self, operator, mock_bot):
        proto = StubText()
        target = make_target()
        record = await operator.send_message(proto, target, keyboard_type="inline")
        assert isinstance(record, BotMessageRecord)

    async def test_send_message_not_saved_to_tree_when_config_false(self, mock_bot):
        instance = await StubDialog(save_bot=False).get_instance(1, 2)
        op = DialogOperator(instance, mock_bot)
        await op.send_message(StubText(), make_target())
        assert op.dialog.current_id is None
