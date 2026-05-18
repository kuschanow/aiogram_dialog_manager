from aiogram_dialog_manager.instance.message import BotMessageRecord, MessageTarget
from tests.conftest import make_tg_message
from tests.helpers import StubText


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


def make_bot_record(tg_message, menu=None) -> BotMessageRecord:
    return BotMessageRecord(type_name="test", menu=menu, telegram_message_instance=tg_message)


class TestReplyToMessage:
    async def test_reply_to_tg_message(self, operator, mock_bot, tg_message):
        proto = StubText()
        record = await operator.reply_to_message(proto, reply_to=tg_message)
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_message.assert_awaited_once()

    async def test_reply_to_bot_message_record(self, operator, mock_bot, tg_message):
        proto = StubText()
        bot_record = make_bot_record(tg_message)
        record = await operator.reply_to_message(proto, reply_to=bot_record)
        assert isinstance(record, BotMessageRecord)

    async def test_reply_with_custom_target(self, operator, mock_bot, tg_message):
        proto = StubText()
        custom_target = make_target(chat_id=999)
        record = await operator.reply_to_message(proto, reply_to=tg_message, target=custom_target)
        assert isinstance(record, BotMessageRecord)
        call_kwargs = mock_bot.send_message.call_args
        assert call_kwargs.kwargs.get("chat_id") == 999
