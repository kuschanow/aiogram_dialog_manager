from aiogram_dialog_manager.instance.message import MessageTarget
from tests.helpers import StubText


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


class TestDeleteNode:
    async def test_delete_node_removes_from_tree(self, operator, tg_message):
        operator.append_user_message(tg_message)
        node_id = operator.dialog.current_id
        await operator.delete_node(node_id)
        assert node_id not in operator.dialog.nodes

    async def test_delete_node_without_delete_messages(self, operator, mock_bot):
        await operator.send_message(StubText(), make_target())
        node_id = operator.dialog.current_id
        await operator.delete_node(node_id, delete_messages=False)
        mock_bot.delete_message.assert_not_awaited()
        assert node_id not in operator.dialog.nodes

    async def test_delete_node_with_delete_messages_calls_bot(self, operator, mock_bot):
        record = await operator.send_message(StubText(), make_target())
        tg = record.telegram_message_instance
        node_id = operator.dialog.current_id
        await operator.delete_node(node_id, delete_messages=True)
        mock_bot.delete_message.assert_awaited_with(
            chat_id=tg.chat.id, message_id=tg.message_id
        )
        assert node_id not in operator.dialog.nodes

    async def test_delete_node_skips_user_message(self, operator, mock_bot, tg_message):
        operator.append_user_message(tg_message)
        node_id = operator.dialog.current_id
        await operator.delete_node(node_id, delete_messages=True)
        mock_bot.delete_message.assert_not_awaited()

    async def test_delete_node_deletes_children(self, operator, mock_bot):
        await operator.send_message(StubText(), make_target())
        n0 = operator.dialog.current_id
        await operator.send_message(StubText(), make_target())
        n1 = operator.dialog.current_id
        await operator.delete_node(n0)
        assert n0 not in operator.dialog.nodes
        assert n1 not in operator.dialog.nodes
