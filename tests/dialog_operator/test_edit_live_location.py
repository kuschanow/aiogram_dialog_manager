from aiogram_dialog_manager.instance.message import BotMessageRecord
from tests.conftest import make_tg_message
from tests.helpers import StubLocation


def make_bot_record(tg_message, menu=None) -> BotMessageRecord:
    return BotMessageRecord(type_name="test", menu=menu, telegram_message_instance=tg_message)


class TestEditLiveLocation:
    async def test_edit_live_location(self, operator, mock_bot, tg_message):
        proto = StubLocation()
        bot_record = make_bot_record(tg_message)
        result = await operator.edit_live_location(bot_record, proto)
        assert result is bot_record
        mock_bot.edit_message_live_location.assert_awaited_once()

    async def test_edit_live_location_result_is_message(self, operator, mock_bot, tg_message):
        proto = StubLocation()
        bot_record = make_bot_record(tg_message)
        new_msg = make_tg_message(message_id=96)
        mock_bot.edit_message_live_location.return_value = new_msg
        await operator.edit_live_location(bot_record, proto)
        assert bot_record.telegram_message_instance is new_msg
