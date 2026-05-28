import asyncio

from aiogram_dialog_manager.instance.message import UserMessageRecord
from tests.conftest import make_tg_message
from tests.helpers import StubDialog


def _make_instance():
    proto = StubDialog()
    return asyncio.run(proto.get_instance(42, 100))


class TestDialogInstance:
    def test_initial_state(self):
        inst = _make_instance()
        assert inst.current_id is None
        assert inst.last_entry is None
        assert inst.entries == []

    def test_append_user_message(self):
        inst = _make_instance()
        msg = make_tg_message()
        record = UserMessageRecord(telegram_message_instance=msg)
        inst.append_message(record)
        assert inst.current_id is not None
        assert inst.last_entry is record
        assert len(inst.entries) == 1

    def test_append_multiple_messages(self):
        inst = _make_instance()
        for i in range(3):
            msg = make_tg_message(message_id=i + 1)
            record = UserMessageRecord(telegram_message_instance=msg)
            inst.append_message(record)
        assert len(inst.entries) == 3

    def test_rollback_to_root(self):
        inst = _make_instance()
        msg = make_tg_message()
        record = UserMessageRecord(telegram_message_instance=msg)
        inst.append_message(record)
        inst.rollback(0)
        assert inst.current_id is None
        assert inst.entries == []

    def test_switch_node_to_none(self):
        inst = _make_instance()
        msg = make_tg_message()
        record = UserMessageRecord(telegram_message_instance=msg)
        inst.append_message(record)
        inst.switch_node(None)
        assert inst.current_id is None

    def test_switch_node_to_existing(self):
        inst = _make_instance()
        msg = make_tg_message()
        record = UserMessageRecord(telegram_message_instance=msg)
        inst.append_message(record)
        node_id = inst.current_id
        inst.switch_node(None)
        inst.switch_node(node_id)
        assert inst.current_id == node_id

    def test_finalize_current_noop_when_none(self):
        inst = _make_instance()
        inst._finalize_current()
        assert inst.current_id is None

    def test_finalize_current_noop_when_already_finalized(self):
        inst = _make_instance()
        msg = make_tg_message()
        record = UserMessageRecord(telegram_message_instance=msg)
        inst.append_message(record)
        node_id = inst.current_id
        inst._finalize_current()
        snap_id_1 = inst.nodes[node_id].data_after_id
        inst._finalize_current()
        snap_id_2 = inst.nodes[node_id].data_after_id
        assert snap_id_1 == snap_id_2

    def test_build_tree_empty(self):
        inst = _make_instance()
        tree = inst.build_tree()
        assert tree.children == []

    def test_build_tree_with_nodes(self):
        inst = _make_instance()
        msg1 = make_tg_message(message_id=1)
        msg2 = make_tg_message(message_id=2)
        inst.append_message(UserMessageRecord(telegram_message_instance=msg1))
        inst.append_message(UserMessageRecord(telegram_message_instance=msg2))
        tree = inst.build_tree()
        assert len(tree.children) == 1
        assert len(tree.children[0].children) == 1

    def test_rollback_restores_data(self):
        inst = _make_instance()
        inst.data["key"] = "value"
        msg = make_tg_message()
        record = UserMessageRecord(telegram_message_instance=msg)
        inst.append_message(record)
        inst.data["key"] = "modified"
        inst.rollback(0)
        assert inst.data.get("key") is None

    def test_rollback_preserve_data(self):
        inst = _make_instance()
        inst.data["key"] = "before"
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message()))
        inst.data["key"] = "current"
        inst.rollback(0, preserve_data=True)
        assert inst.current_id is None
        assert inst.data["key"] == "current"

    def test_switch_node_uses_data_after_when_finalized(self):
        inst = _make_instance()
        msg = make_tg_message()
        record = UserMessageRecord(telegram_message_instance=msg)
        inst.append_message(record)
        node_id = inst.current_id
        inst.data["k"] = "after"
        inst._finalize_current()
        inst.switch_node(None)
        inst.switch_node(node_id)
        assert inst.data.get("k") == "after"

    def test_root_children_ids_populated(self):
        inst = _make_instance()
        msg = make_tg_message()
        inst.append_message(UserMessageRecord(telegram_message_instance=msg))
        assert len(inst.root_children_ids) == 1


class TestCollectSubtreeIds:
    def test_single_node(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message()))
        node_id = inst.current_id
        assert inst.collect_subtree_ids(node_id) == [node_id]

    def test_with_children(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(1)))
        n0 = inst.current_id
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(2)))
        n1 = inst.current_id
        assert set(inst.collect_subtree_ids(n0)) == {n0, n1}


class TestDeleteNodeInstance:
    def test_delete_current_root_node(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message()))
        node_id = inst.current_id
        inst.delete_node(node_id)
        assert inst.current_id is None
        assert node_id not in inst.nodes
        assert node_id not in inst.root_children_ids

    def test_delete_ancestor_of_current_and_cleans_orphaned_snapshots(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(1)))
        n0 = inst.current_id
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(2)))
        n1 = inst.current_id
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(3)))
        snap_count_before = len(inst.snapshots)
        inst.delete_node(n1)
        assert inst.current_id == n0
        assert n1 not in inst.nodes
        assert len(inst.snapshots) < snap_count_before

    def test_delete_non_current_root_node(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(1)))
        n0 = inst.current_id
        inst.switch_node(None)
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(2)))
        n1 = inst.current_id
        inst.delete_node(n0)
        assert n0 not in inst.nodes
        assert inst.current_id == n1

    def test_delete_non_current_non_root_node(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(1)))
        n0 = inst.current_id
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(2)))
        n1 = inst.current_id
        inst.switch_node(n0)
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(3)))
        n2 = inst.current_id
        inst.delete_node(n1)
        assert n1 not in inst.nodes
        assert inst.current_id == n2
        assert n1 not in inst.nodes[n0].children_ids

    def test_delete_node_preserve_data(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message()))
        node_id = inst.current_id
        inst.data["key"] = "current"
        inst.delete_node(node_id, preserve_data=True)
        assert node_id not in inst.nodes
        assert inst.data["key"] == "current"


class TestDeleteCurrentBranch:
    def test_empty_path_noop(self):
        inst = _make_instance()
        inst.delete_current_branch()
        assert inst.current_id is None
        assert inst.nodes == {}

    def test_single_node(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message()))
        node_id = inst.current_id
        inst.delete_current_branch()
        assert inst.current_id is None
        assert node_id not in inst.nodes

    def test_sibling_reparented_to_root(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(1)))
        n0 = inst.current_id
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(2)))
        n1 = inst.current_id
        inst.switch_node(n0)
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(3)))
        n2 = inst.current_id
        inst.delete_current_branch()
        assert n0 not in inst.nodes
        assert n2 not in inst.nodes
        assert n1 in inst.nodes
        assert n1 in inst.root_children_ids
        assert inst.nodes[n1].parent_id is None

    def test_resets_data(self):
        inst = _make_instance()
        inst.data["key"] = "val"
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message()))
        inst.delete_current_branch()
        assert "key" not in inst.data

    def test_delete_current_branch_preserve_data(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message()))
        inst.data["key"] = "current"
        inst.delete_current_branch(preserve_data=True)
        assert inst.current_id is None
        assert inst.data["key"] == "current"


class TestClearAllNodes:
    def test_clears_everything(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(1)))
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message(2)))
        inst.clear_all_nodes()
        assert inst.nodes == {}
        assert inst.root_children_ids == []
        assert inst.current_id is None

    def test_preserves_initial_snapshot(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message()))
        initial_snap_id = inst.initial_snapshot_id
        inst.clear_all_nodes()
        assert initial_snap_id in inst.snapshots
        assert len(inst.snapshots) == 1

    def test_clear_all_nodes_preserve_data(self):
        inst = _make_instance()
        inst.append_message(UserMessageRecord(telegram_message_instance=make_tg_message()))
        inst.data["key"] = "current"
        inst.clear_all_nodes(preserve_data=True)
        assert inst.nodes == {}
        assert inst.data["key"] == "current"
