from aiogram.exceptions import TelegramBadRequest

from aiogram_dialog_manager.instance.message import MessageTarget
from tests.helpers import StubText


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


class TestRollbackAndSwitchNode:
    async def test_rollback(self, operator, tg_message):
        operator.append_user_message(tg_message)
        await operator.rollback(0)
        assert operator.dialog.current_id is None

    async def test_rollback_with_delete_nodes(self, operator, tg_message):
        operator.append_user_message(tg_message)
        node_id = operator.dialog.current_id
        await operator.rollback(0, delete_nodes=True)
        assert operator.dialog.current_id is None
        assert node_id not in operator.dialog.nodes

    async def test_rollback_with_delete_nodes_and_messages(self, operator, mock_bot):
        record = await operator.send_message(StubText(), make_target())
        tg = record.telegram_message_instance
        await operator.rollback(0, delete_nodes=True, delete_messages=True)
        mock_bot.delete_message.assert_awaited_with(
            chat_id=tg.chat.id, message_id=tg.message_id
        )
        assert len(operator.dialog.nodes) == 0

    async def test_rollback_with_delete_nodes_no_messages(self, operator, mock_bot):
        await operator.send_message(StubText(), make_target())
        node_id = operator.dialog.current_id
        await operator.rollback(0, delete_nodes=True, delete_messages=False)
        mock_bot.delete_message.assert_not_awaited()
        assert node_id not in operator.dialog.nodes

    async def test_rollback_delete_messages_skips_user_message(self, operator, mock_bot, tg_message):
        operator.append_user_message(tg_message)
        await operator.rollback(0, delete_nodes=True, delete_messages=True)
        mock_bot.delete_message.assert_not_awaited()

    async def test_rollback_delete_messages_handles_bad_request(self, operator, mock_bot):
        await operator.send_message(StubText(), make_target())
        mock_bot.delete_message.side_effect = TelegramBadRequest(
            method="deleteMessage", message="not found"
        )
        await operator.rollback(0, delete_nodes=True, delete_messages=True)

    def test_switch_node_to_none(self, operator, tg_message):
        operator.append_user_message(tg_message)
        operator.switch_node(None)
        assert operator.dialog.current_id is None

    def test_switch_node_to_existing(self, operator, tg_message):
        operator.append_user_message(tg_message)
        node_id = operator.dialog.current_id
        operator.switch_node(None)
        operator.switch_node(node_id)
        assert operator.dialog.current_id == node_id
