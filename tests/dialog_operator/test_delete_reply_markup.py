from aiogram_dialog_manager.instance.menu import RemoveKeyboardMenuInstance
from aiogram_dialog_manager.instance.message import BotMessageRecord
from tests.conftest import make_tg_message


def _make_bot_record(tg_message) -> BotMessageRecord:
    menu = RemoveKeyboardMenuInstance(type_name="menu")
    return BotMessageRecord(type_name="test", menu=menu, telegram_message_instance=tg_message)


class TestDeleteReplyMarkup:
    async def test_delete_reply_markup_calls_api(self, operator, mock_bot, tg_message):
        bot_record = _make_bot_record(tg_message)
        result = await operator.delete_reply_markup(bot_record)
        assert result is bot_record
        mock_bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=tg_message.chat.id,
            message_id=tg_message.message_id,
            business_connection_id=tg_message.business_connection_id,
            reply_markup=None,
        )

    async def test_delete_reply_markup_clears_menu(self, operator, mock_bot, tg_message):
        bot_record = _make_bot_record(tg_message)
        assert bot_record.menu is not None
        await operator.delete_reply_markup(bot_record)
        assert bot_record.menu is None

    async def test_delete_reply_markup_updates_tg_message(self, operator, mock_bot, tg_message):
        bot_record = _make_bot_record(tg_message)
        new_msg = make_tg_message(message_id=99)
        mock_bot.edit_message_reply_markup.return_value = new_msg
        await operator.delete_reply_markup(bot_record)
        assert bot_record.telegram_message_instance is new_msg