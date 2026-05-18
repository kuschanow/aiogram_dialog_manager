class TestRollbackAndSwitchNode:
    def test_rollback(self, operator, tg_message):
        operator.append_user_message(tg_message)
        operator.rollback(0)
        assert operator.dialog.current_id is None

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
