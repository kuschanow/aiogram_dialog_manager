from aiogram_dialog_manager.instance.message import BotMessageRecord
from tests.conftest import make_tg_message
from tests.helpers import StubPhoto


def make_bot_record(tg_message, menu=None) -> BotMessageRecord:
    return BotMessageRecord(type_name="test", menu=menu, telegram_message_instance=tg_message)


class TestEditMessageMedia:
    async def test_edit_media(self, operator, mock_bot, tg_message):
        proto = StubPhoto()
        bot_record = make_bot_record(tg_message)
        result = await operator.edit_message_media(bot_record, proto)
        assert result is bot_record
        mock_bot.edit_message_media.assert_awaited_once()

    async def test_edit_media_result_is_message(self, operator, mock_bot, tg_message):
        proto = StubPhoto()
        bot_record = make_bot_record(tg_message)
        new_msg = make_tg_message(message_id=97)
        mock_bot.edit_message_media.return_value = new_msg
        await operator.edit_message_media(bot_record, proto)
        assert bot_record.telegram_message_instance is new_msg
