"""Tests for the core model: DialogSpec, WindowSpec, MenuSpec, serialization."""
import json

import pytest
from pydantic import ValidationError

from aiogram_dialog_manager.spec import (
    DialogSpec,
    MenuSpec,
    PhotoContentSpec,
    RowNode,
    SPEC_VERSION,
    TextContentSpec,
    WindowSpec,
)


def make_minimal_dict() -> dict:
    return {
        "version": 1,
        "name": "settings",
        "windows": {
            "main": {
                "content": {"type": "text", "text": "Hello"},
                "menu": {"rows": [[{"type": "button", "name": "save", "text": "Save"}]]},
            },
        },
    }


class TestMenuSpec:
    def test_plain_list_rows_wrapped_into_row_nodes(self):
        menu = MenuSpec(rows=[[{"type": "button", "name": "a", "text": "A"}]])
        assert isinstance(menu.rows[0], RowNode)

    def test_tuple_rows_wrapped(self):
        menu = MenuSpec(rows=[({"type": "button", "name": "a", "text": "A"},)])
        assert isinstance(menu.rows[0], RowNode)

    def test_node_rows_kept(self):
        menu = MenuSpec(rows=[{"type": "row", "items": []}])
        assert isinstance(menu.rows[0], RowNode)

    def test_non_list_rows_rejected(self):
        with pytest.raises(ValidationError):
            MenuSpec(rows="not a list")

    def test_empty_rows_rejected(self):
        with pytest.raises(ValidationError):
            MenuSpec(rows=[])

    def test_keyboard_type_validated(self):
        with pytest.raises(ValidationError):
            MenuSpec(rows=[[]], keyboard_type="magic")

    def test_reply_parameters_accept_expressions(self):
        menu = MenuSpec(rows=[[]], reply_parameters={"input_field_placeholder": {"type": "path", "path": "data.ph"}})
        assert menu.reply_parameters["input_field_placeholder"].path == "data.ph"


class TestWindowSpec:
    def test_content_union_by_type(self):
        window = WindowSpec(content={"type": "photo", "photo": "file_id"})
        assert isinstance(window.content, PhotoContentSpec)

    def test_non_content_node_rejected(self):
        with pytest.raises(ValidationError, match="Window content must be a content node"):
            WindowSpec(content={"type": "path", "path": "data.x"})

    def test_scalar_content_rejected(self):
        with pytest.raises(ValidationError):
            WindowSpec(content="just text")


class TestDialogSpec:
    def test_from_dict(self):
        spec = DialogSpec.from_dict(make_minimal_dict())
        assert spec.name == "settings"
        assert isinstance(spec.windows["main"].content, TextContentSpec)

    def test_version_default(self):
        spec = DialogSpec(name="d", windows={"w": {"content": {"type": "text", "text": "x"}}})
        assert spec.version == SPEC_VERSION

    def test_unsupported_version_rejected(self):
        payload = make_minimal_dict() | {"version": 99}
        with pytest.raises(ValidationError, match="Unsupported spec version 99"):
            DialogSpec.from_dict(payload)

    def test_invalid_dialog_name_rejected(self):
        with pytest.raises(ValidationError):
            DialogSpec(name="bad name", windows={"w": {"content": {"type": "text", "text": "x"}}})

    def test_invalid_window_name_rejected(self):
        with pytest.raises(ValidationError):
            DialogSpec(name="d", windows={"bad name": {"content": {"type": "text", "text": "x"}}})

    def test_windows_required_non_empty(self):
        with pytest.raises(ValidationError):
            DialogSpec(name="d", windows={})

    def test_unknown_root_keys_rejected(self):
        with pytest.raises(ValidationError):
            DialogSpec.from_dict(make_minimal_dict() | {"actions": []})

    def test_json_roundtrip_preserves_model(self):
        payload = make_minimal_dict()
        payload["windows"]["main"]["menu"]["rows"].append({
            "type": "if",
            "when": {"type": "op", "op": ">", "args": [{"type": "path", "path": "data.page"}, 0]},
            "then": {"type": "row", "items": [{"type": "ref", "name": "back"}]},
        })
        payload["defs"] = {"back": {"type": "button", "name": "back", "text": {"type": "t", "key": "back"}}}
        spec = DialogSpec.from_dict(payload)
        dumped = json.loads(json.dumps(spec.to_dict()))
        assert DialogSpec.from_dict(dumped) == spec

    def test_to_dict_is_canonical(self):
        spec = DialogSpec.from_dict(make_minimal_dict())
        dumped = spec.to_dict()
        assert dumped["version"] == 1
        # plain-list row sugar is normalized to an explicit row node
        assert dumped["windows"]["main"]["menu"]["rows"][0]["type"] == "row"
