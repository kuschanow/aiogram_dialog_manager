from aiogram_dialog_manager.instance.message import BotMessageRecord
from tests.conftest import make_tg_message
from tests.helpers import StubPhoto, StubText


def make_bot_record(tg_message, menu=None) -> BotMessageRecord:
    return BotMessageRecord(type_name="test", menu=menu, telegram_message_instance=tg_message)


class TestEditMessage:
    async def test_edit_text_message(self, operator, mock_bot, tg_message):
        proto = StubText()
        bot_record = make_bot_record(tg_message)
        result = await operator.edit_message(bot_record, proto)
        assert result is bot_record
        mock_bot.edit_message_text.assert_awaited_once()

    async def test_edit_text_message_result_is_message(self, operator, mock_bot, tg_message):
        proto = StubText()
        bot_record = make_bot_record(tg_message)
        new_msg = make_tg_message(message_id=99)
        mock_bot.edit_message_text.return_value = new_msg
        await operator.edit_message(bot_record, proto)
        assert bot_record.telegram_message_instance is new_msg

    async def test_edit_caption_media(self, operator, mock_bot, tg_message):
        proto = StubPhoto()
        bot_record = make_bot_record(tg_message)
        result = await operator.edit_message(bot_record, proto)
        assert result is bot_record
        mock_bot.edit_message_caption.assert_awaited_once()

    async def test_edit_caption_result_is_message(self, operator, mock_bot, tg_message):
        proto = StubPhoto()
        bot_record = make_bot_record(tg_message)
        new_msg = make_tg_message(message_id=98)
        mock_bot.edit_message_caption.return_value = new_msg
        await operator.edit_message(bot_record, proto)
        assert bot_record.telegram_message_instance is new_msg
