from aiogram_dialog_manager.instance.message import BotMessageRecord
from tests.conftest import make_tg_message
from tests.helpers import StubMenu


def make_bot_record(tg_message, menu=None) -> BotMessageRecord:
    return BotMessageRecord(type_name="test", menu=menu, telegram_message_instance=tg_message)


class TestEditReplyMarkup:
    async def test_edit_reply_markup(self, operator, mock_bot, tg_message):
        menu_proto = StubMenu()
        bot_record = make_bot_record(tg_message)
        result = await operator.edit_reply_markup(bot_record, menu_proto)
        assert result is bot_record
        mock_bot.edit_message_reply_markup.assert_awaited_once()

    async def test_edit_reply_markup_result_is_message(self, operator, mock_bot, tg_message):
        menu_proto = StubMenu()
        bot_record = make_bot_record(tg_message)
        new_msg = make_tg_message(message_id=95)
        mock_bot.edit_message_reply_markup.return_value = new_msg
        await operator.edit_reply_markup(bot_record, menu_proto)
        assert bot_record.telegram_message_instance is new_msg
