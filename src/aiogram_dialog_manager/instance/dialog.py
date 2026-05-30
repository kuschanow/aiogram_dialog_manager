import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import Field, ConfigDict

from aiogram_dialog_manager.instance.base import BaseDialogModel
from aiogram_dialog_manager.instance.message import AnyMessageRecord


class DialogNode(BaseDialogModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    message: AnyMessageRecord = Field(..., description="The message associated with this node.")
    parent_id: Optional[str] = Field(None, description="None if the parent is the virtual root.")
    children_ids: list[str] = Field(default_factory=list)
    data_before_id: str = Field(..., description="Snapshot ID of dialog data before this message was processed.")
    data_after_id: Optional[str] = Field(None, description="Snapshot ID of dialog data after this message was processed. None until the node is finalized.")


class TreeNodeView(BaseDialogModel):
    node_id: str = Field(..., description="The ID of the corresponding DialogNode.")
    message: AnyMessageRecord = Field(..., description="The message associated with this node.")
    data_before: dict = Field(..., description="Dialog data state before this message was processed.")
    data_after: Optional[dict] = Field(None, description="Dialog data state after this message was processed. None if the node has not been finalized yet.")
    children: list["TreeNodeView"] = Field(default_factory=list, description="Child nodes representing branches that follow this message.")


class TreeView(BaseDialogModel):
    children: list[TreeNodeView] = Field(default_factory=list, description="Children of the virtual root, i.e. all possible first messages of the dialog.")


class DialogConfig(BaseDialogModel):
    save_user_message_nodes: bool = Field(False, description="Whether to preserve dialog nodes when a user message is edited or deleted.")
    save_bot_message_nodes: bool = Field(True, description="Whether to preserve dialog nodes when a bot message is edited or deleted.")
    allow_reply_lookup: bool = Field(False, description="Whether to allow resolving this dialog via reply to one of its bot messages.")
    index_bot_messages: bool = Field(False, description="Whether to index bot messages so the dialog can be resolved via reply to them.")
    index_user_messages: bool = Field(False, description="Whether to index user messages so the dialog can be resolved via reply to them.")
    save_foreign_user_messages: bool = Field(False, description="Whether to save messages from users other than the dialog owner. Only effective when save_user_message_nodes is True.")


class DialogInstance(BaseDialogModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="The unique identifier of the dialog instance.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of dialog creation.")
    config: DialogConfig = Field(default_factory=DialogConfig, frozen=True,
                                 description="Immutable operator configuration. Set once at instance creation from the dialog prototype.")
    type_name: str = Field(..., description="Name of the dialog prototype.")
    user_id: int = Field(..., description="Telegram user ID of the dialog owner.")
    chat_id: int = Field(..., description="Telegram chat ID where the dialog takes place.")
    nodes: dict[str, DialogNode] = Field(default_factory=dict, description="Flat storage of all dialog nodes keyed by their ID.")
    snapshots: dict[str, dict] = Field(default_factory=dict,
                                       description="Flat storage of all data snapshots keyed by their ID. Each snapshot is stored once and referenced by nodes via data_before_id and data_after_id.")
    initial_snapshot_id: str = Field(..., description="Snapshot ID of the dialog data before any messages were processed. Shared as data_before_id by all root-level nodes.")
    root_children_ids: list[str] = Field(default_factory=list, description="IDs of the direct children of the virtual root, i.e. all possible first messages of the dialog.")
    current_id: Optional[str] = Field(None, description="ID of the currently active node. None if the cursor is at the virtual root.")
    data: dict = Field(default_factory=dict, description="Current working dialog data. Saved as a snapshot when the active node is finalized.")

    def _path_to_current(self) -> list[str]:
        path, node_id = [], self.current_id
        while node_id is not None:
            path.append(node_id)
            node_id = self.nodes[node_id].parent_id
        return list(reversed(path))

    def _finalize_current(self) -> None:
        if self.current_id is None or self.nodes[self.current_id].data_after_id is not None:
            return
        snap_id = uuid.uuid4().hex
        self.snapshots[snap_id] = self.data.copy()
        self.nodes[self.current_id].data_after_id = snap_id

    @property
    def last_entry(self) -> Optional[AnyMessageRecord]:
        return self.nodes[self.current_id].message if self.current_id is not None else None

    @property
    def entries(self) -> list[AnyMessageRecord]:
        path, node_id = [], self.current_id
        while node_id is not None:
            node = self.nodes[node_id]
            path.append(node.message)
            node_id = node.parent_id
        return list(reversed(path))

    def build_tree(self) -> TreeView:
        def build(node_id: str) -> TreeNodeView:
            node = self.nodes[node_id]
            return TreeNodeView(
                node_id=node_id,
                message=node.message,
                data_before=self.snapshots[node.data_before_id],
                data_after=self.snapshots[node.data_after_id] if node.data_after_id else None,
                children=[build(child_id) for child_id in node.children_ids]
            )

        return TreeView(children=[build(child_id) for child_id in self.root_children_ids])

    def append_message(self, message: AnyMessageRecord) -> None:
        self._finalize_current()
        data_before_id = (
            self.nodes[self.current_id].data_after_id
            if self.current_id is not None
            else self.initial_snapshot_id
        )
        node = DialogNode(
            message=message,
            parent_id=self.current_id,
            data_before_id=data_before_id,
        )
        self.nodes[node.id] = node
        if self.current_id is None:
            self.root_children_ids.append(node.id)
        else:
            self.nodes[self.current_id].children_ids.append(node.id)
        self.current_id = node.id

    def collect_subtree_ids(self, node_id: str) -> list[str]:
        result = []
        stack = [node_id]
        while stack:
            nid = stack.pop()
            result.append(nid)
            stack.extend(self.nodes[nid].children_ids)
        return result

    def _cleanup_snapshots(self) -> None:
        in_use = {self.initial_snapshot_id}
        for node in self.nodes.values():
            in_use.add(node.data_before_id)
            if node.data_after_id:
                in_use.add(node.data_after_id)
        for snap_id in list(self.snapshots.keys()):
            if snap_id not in in_use:
                del self.snapshots[snap_id]

    def delete_node(self, node_id: str, preserve_data: bool = False) -> None:
        current_data = self.data.copy() if preserve_data else None
        ids_to_delete = set(self.collect_subtree_ids(node_id))
        if self.current_id in ids_to_delete:
            parent_id = self.nodes[node_id].parent_id
            self.current_id = parent_id
            if parent_id is not None:
                parent = self.nodes[parent_id]
                self.data = self.snapshots[parent.data_after_id or parent.data_before_id].copy()
            else:
                self.data = self.snapshots[self.initial_snapshot_id].copy()
        parent_id = self.nodes[node_id].parent_id
        if parent_id is None:
            self.root_children_ids.remove(node_id)
        else:
            self.nodes[parent_id].children_ids.remove(node_id)
        for nid in ids_to_delete:
            del self.nodes[nid]
        self._cleanup_snapshots()
        if preserve_data:
            self.data = current_data

    def delete_current_branch(self, preserve_data: bool = False) -> None:
        current_data = self.data.copy() if preserve_data else None
        path = self._path_to_current()
        if not path:
            return
        # Pre-compute non-path children for each node before modifying any children lists.
        non_path_children_by_node: dict[str, list[str]] = {}
        for i, node_id in enumerate(path):
            path_child_id = path[i + 1] if i + 1 < len(path) else None
            non_path_children_by_node[node_id] = [
                c for c in self.nodes[node_id].children_ids if c != path_child_id
            ]
        # path[0] is always a root node (parent_id=None), so remove from root_children_ids.
        self.root_children_ids.remove(path[0])
        for node_id in path:
            # Non-path children bubble up to the virtual root.
            for child_id in non_path_children_by_node[node_id]:
                self.nodes[child_id].parent_id = None
                self.root_children_ids.append(child_id)
            del self.nodes[node_id]
        self.current_id = None
        self.data = self.snapshots[self.initial_snapshot_id].copy()
        self._cleanup_snapshots()
        if preserve_data:
            self.data = current_data

    def clear_all_nodes(self, preserve_data: bool = False) -> None:
        current_data = self.data.copy() if preserve_data else None
        self.nodes.clear()
        self.root_children_ids.clear()
        self.current_id = None
        self.data = self.snapshots[self.initial_snapshot_id].copy()
        initial_snap = self.snapshots[self.initial_snapshot_id]
        self.snapshots.clear()
        self.snapshots[self.initial_snapshot_id] = initial_snap
        if preserve_data:
            self.data = current_data

    def rollback(self, index: int, preserve_data: bool = False) -> None:
        current_data = self.data.copy() if preserve_data else None
        path = self._path_to_current()
        self._finalize_current()
        self.current_id = self.nodes[path[index]].parent_id
        self.data = self.snapshots[self.nodes[path[index]].data_before_id].copy()
        if preserve_data:
            self.data = current_data

    def switch_node(self, node_id: Optional[str]) -> None:
        self._finalize_current()
        self.current_id = node_id
        if node_id is not None:
            node = self.nodes[node_id]
            snap_id = node.data_after_id or node.data_before_id
            self.data = self.snapshots[snap_id].copy()
        else:
            self.data = self.snapshots[self.initial_snapshot_id].copy()
