from aiogram_dialog_manager.instance.message import BotMessageRecord


def make_bot_record(tg_message, menu=None) -> BotMessageRecord:
    return BotMessageRecord(type_name="test", menu=menu, telegram_message_instance=tg_message)


class TestDeleteMessage:
    async def test_delete_message(self, operator, mock_bot, tg_message):
        bot_record = make_bot_record(tg_message)
        await operator.delete_message(bot_record)
        mock_bot.delete_message.assert_awaited_once_with(
            chat_id=tg_message.chat.id, message_id=tg_message.message_id
        )
