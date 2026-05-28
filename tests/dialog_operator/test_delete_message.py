from aiogram_dialog_manager.instance.message import BotMessageRecord, MessageTarget
from tests.helpers import StubText


def make_bot_record(tg_message, menu=None) -> BotMessageRecord:
    return BotMessageRecord(type_name="test", menu=menu, telegram_message_instance=tg_message)


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


class TestDeleteMessage:
    async def test_delete_message(self, operator, mock_bot, tg_message):
        bot_record = make_bot_record(tg_message)
        await operator.delete_message(bot_record)
        mock_bot.delete_message.assert_awaited_once_with(
            chat_id=tg_message.chat.id, message_id=tg_message.message_id
        )

    async def test_delete_message_with_delete_node(self, operator, mock_bot):
        record = await operator.send_message(StubText(), make_target())
        node_id = operator.dialog.current_id
        await operator.delete_message(record, delete_node=True)
        assert node_id not in operator.dialog.nodes

    async def test_delete_message_delete_node_not_tracked(self, operator, mock_bot, tg_message):
        bot_record = make_bot_record(tg_message)
        await operator.delete_message(bot_record, delete_node=True)
        assert operator.dialog.nodes == {}
