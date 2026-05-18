from aiogram.exceptions import TelegramBadRequest

from aiogram_dialog_manager.instance.message import BotMessageInstance, MessageTarget
from tests.helpers import StubText


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


class TestDeleteAllMessages:
    async def test_delete_all_messages_full_tree(self, operator, mock_bot):
        proto = StubText()
        await operator.send_message(proto, make_target())
        await operator.delete_all_messages(only_current_branch=False)
        mock_bot.delete_message.assert_awaited()

    async def test_delete_all_messages_current_branch(self, operator, mock_bot):
        proto = StubText()
        await operator.send_message(proto, make_target())
        await operator.delete_all_messages(only_current_branch=True)
        mock_bot.delete_message.assert_awaited()

    async def test_delete_all_messages_ignores_user_messages(self, operator, mock_bot, tg_message):
        operator.append_user_message(tg_message)
        await operator.delete_all_messages()
        mock_bot.delete_message.assert_not_awaited()

    async def test_delete_all_messages_swallows_bad_request(self, operator, mock_bot):
        proto = StubText()
        await operator.send_message(proto, make_target())
        mock_bot.delete_message.side_effect = TelegramBadRequest(
            method="deleteMessage", message="not found"
        )
        await operator.delete_all_messages()

    async def test_get_message_instance(self, operator):
        proto = StubText()
        instance = await operator.get_message_instance(proto, None)
        assert isinstance(instance, BotMessageInstance)
