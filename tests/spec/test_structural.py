"""Tests for structural constructs: if, foreach, chunk, slice, row, button, media_item."""
import pytest
from aiogram.types import InputMediaDocument, InputMediaPhoto

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.spec import (
    OMIT,
    ButtonSpec,
    ChunkNode,
    ExpressionEvaluationError,
    ForeachNode,
    IfNode,
    MediaItemNode,
    OpNode,
    PathNode,
    RowNode,
    SliceNode,
    Spliced,
    evaluate_value,
)


class TestIfNode:
    async def test_then_branch(self, scope):
        node = IfNode(when=True, then="yes", else_="no")
        assert await node.evaluate(scope) == "yes"

    async def test_else_branch(self, scope):
        node = IfNode(when=False, then="yes", else_="no")
        assert await node.evaluate(scope) == "no"

    async def test_missing_else_yields_omit(self, scope):
        assert await IfNode(when=False, then="yes").evaluate(scope) is OMIT

    async def test_omit_is_none_in_value_context(self, scope):
        assert await evaluate_value(IfNode(when=False, then="yes"), scope) is None

    async def test_omit_dropped_in_list_context(self, scope):
        result = await evaluate_value(["a", IfNode(when=False, then="b"), "c"], scope)
        assert result == ["a", "c"]

    async def test_explicit_null_else_is_kept(self, scope):
        node = IfNode.model_validate({"type": "if", "when": False, "then": "yes", "else": None})
        assert await node.evaluate(scope) is None

    async def test_branch_may_splice(self, make_scope):
        scope = make_scope(data={"items": [1, 2]})
        node = IfNode(when=True, then=ForeachNode(over=PathNode(path="data.items"), body=PathNode(path="item")))
        result = await node.evaluate(scope)
        assert isinstance(result, Spliced)
        assert (await evaluate_value([node], scope)) == [1, 2]

    def test_serialization_omits_unset_else(self):
        node = IfNode(when=True, then="x")
        assert "else" not in node.model_dump(by_alias=True)
        assert "else_" not in node.model_dump()

    def test_serialization_keeps_set_else(self):
        node = IfNode(when=True, then="x", else_="y")
        assert node.model_dump(by_alias=True)["else"] == "y"


class TestForeachNode:
    async def test_item_and_index_scope(self, make_scope):
        scope = make_scope(data={"players": [{"name": "A"}, {"name": "B"}]})
        node = ForeachNode(
            over=PathNode(path="data.players"),
            body=[PathNode(path="index"), PathNode(path="item.name")],
        )
        result = await node.evaluate(scope)
        assert isinstance(result, Spliced)
        assert result.items == [[0, "A"], [1, "B"]]

    async def test_splices_into_enclosing_list(self, make_scope):
        scope = make_scope(data={"items": [1, 2]})
        node = ForeachNode(over=PathNode(path="data.items"), body=PathNode(path="item"))
        assert await evaluate_value(["start", node, "end"], scope) == ["start", 1, 2, "end"]

    async def test_nested_foreach_shadows_item(self, make_scope):
        scope = make_scope(data={"rows": [[1, 2], [3]]})
        node = ForeachNode(
            over=PathNode(path="data.rows"),
            body=ForeachNode(over=PathNode(path="item"), body=PathNode(path="item")),
        )
        assert await evaluate_value([node], scope) == [1, 2, 3]

    async def test_body_omit_skipped(self, make_scope):
        scope = make_scope(data={"items": [1, 2, 3]})
        node = ForeachNode(
            over=PathNode(path="data.items"),
            body=IfNode(when=OpNode(op=">", args=[PathNode(path="item"), 1]), then=PathNode(path="item")),
        )
        assert await evaluate_value([node], scope) == [2, 3]

    async def test_non_list_over_raises(self, scope):
        with pytest.raises(ExpressionEvaluationError, match="'foreach' expects 'over'"):
            await ForeachNode(over=5, body=1).evaluate(scope)

    async def test_spliced_unwraps_to_list_in_value_context(self, make_scope):
        scope = make_scope(data={"items": [1, 2]})
        node = ForeachNode(over=PathNode(path="data.items"), body=PathNode(path="item"))
        assert await evaluate_value(node, scope) == [1, 2]


class TestChunkNode:
    async def test_chunks_flat_items_into_rows(self, scope):
        node = ChunkNode(size=2, items=["a", "b", "c", "d", "e"])
        result = await node.evaluate(scope)
        assert isinstance(result, Spliced)
        assert result.items == [["a", "b"], ["c", "d"], ["e"]]

    async def test_size_is_expression(self, make_scope):
        scope = make_scope(data={"n": 3})
        node = ChunkNode(size=PathNode(path="data.n"), items=["a", "b", "c"])
        assert (await node.evaluate(scope)).items == [["a", "b", "c"]]

    async def test_items_spliced_before_chunking(self, make_scope):
        scope = make_scope(data={"items": [1, 2, 3]})
        node = ChunkNode(size=2, items=[ForeachNode(over=PathNode(path="data.items"), body=PathNode(path="item"))])
        assert (await node.evaluate(scope)).items == [[1, 2], [3]]

    @pytest.mark.parametrize("size", [0, -1, "2", 2.0, True])
    async def test_invalid_size_raises(self, scope, size):
        with pytest.raises(ExpressionEvaluationError, match="'chunk' size"):
            await ChunkNode(size=size, items=["a"]).evaluate(scope)


class TestSliceNode:
    async def test_slice_with_expression_bounds(self, make_scope):
        scope = make_scope(data={"items": [0, 1, 2, 3, 4], "page": 1})
        node = SliceNode(
            over=PathNode(path="data.items"),
            start=OpNode(op="*", args=[PathNode(path="data.page"), 2]),
            stop=OpNode(op="*", args=[OpNode(op="+", args=[PathNode(path="data.page"), 1]), 2]),
        )
        assert await node.evaluate(scope) == [2, 3]

    async def test_open_bounds(self, make_scope):
        scope = make_scope(data={"items": [0, 1, 2]})
        assert await SliceNode(over=PathNode(path="data.items")).evaluate(scope) == [0, 1, 2]
        assert await SliceNode(over=PathNode(path="data.items"), start=1).evaluate(scope) == [1, 2]
        assert await SliceNode(over=PathNode(path="data.items"), stop=2).evaluate(scope) == [0, 1]

    async def test_non_list_over_raises(self, scope):
        with pytest.raises(ExpressionEvaluationError, match="'slice' expects 'over'"):
            await SliceNode(over="abc").evaluate(scope)

    async def test_bad_bounds_raise(self, make_scope):
        scope = make_scope(data={"items": [1, 2]})
        with pytest.raises(ExpressionEvaluationError, match="'slice' failed"):
            await SliceNode(over=PathNode(path="data.items"), start="x").evaluate(scope)


class TestRowNode:
    async def test_renders_items_with_splicing(self, make_scope):
        scope = make_scope(data={"items": [1, 2]})
        node = RowNode(items=[
            "first",
            ForeachNode(over=PathNode(path="data.items"), body=PathNode(path="item")),
            IfNode(when=False, then="dropped"),
        ])
        assert await node.evaluate(scope) == ["first", 1, 2]


class TestButtonSpec:
    async def test_evaluates_to_button_instance(self, make_scope):
        scope = make_scope(data={"page": 2})
        spec = ButtonSpec(name="save", text="Save", data={"page": PathNode(path="data.page")})
        instance = await spec.evaluate(scope)
        assert isinstance(instance, ButtonInstance)
        assert instance.text == "Save"
        assert instance.type_name == "dlg:win:save"
        assert instance.data == {"page": 2}
        assert instance.inline_additional_parameters is None
        assert instance.common_additional_parameters is None

    async def test_type_name_without_window(self, make_scope):
        scope = make_scope(window_name=None)
        spec = ButtonSpec(name="save", text="Save")
        assert spec.type_name(scope) == "dlg:save"

    async def test_text_fragments_joined(self, make_scope):
        scope = make_scope(data={"n": 3})
        spec = ButtonSpec(name="b", text=["Page ", PathNode(path="data.n"), PathNode(path="data.missing")])
        assert await spec.evaluate_text(scope) == "Page 3"

    async def test_non_string_text_coerced(self, scope):
        spec = ButtonSpec(name="b", text=42)
        assert await spec.evaluate_text(scope) == "42"

    async def test_none_text_raises(self, make_scope):
        scope = make_scope(data={})
        spec = ButtonSpec(name="b", text=PathNode(path="data.missing"))
        with pytest.raises(ExpressionEvaluationError, match="Text of button 'b'"):
            await spec.evaluate_text(scope)

    async def test_inline_parameters_evaluated(self, make_scope):
        scope = make_scope(data={"slug": "abc"})
        spec = ButtonSpec(
            name="site", text="Site",
            inline={"url": OpNode(op="+", args=["https://example.com/", PathNode(path="data.slug")])},
        )
        instance = await spec.evaluate(scope)
        assert instance.inline_additional_parameters.url == "https://example.com/abc"

    async def test_common_parameters_evaluated(self, scope):
        spec = ButtonSpec(name="contact", text="Phone", common={"request_contact": True})
        instance = await spec.evaluate(scope)
        assert instance.common_additional_parameters.request_contact is True

    def test_name_must_be_identifier(self):
        with pytest.raises(ValueError):
            ButtonSpec(name="bad name", text="x")

    async def test_foreach_parameterizes_payload(self, make_scope):
        scope = make_scope(data={"players": [{"id": 10}, {"id": 20}]})
        node = ForeachNode(
            over=PathNode(path="data.players"),
            body=ButtonSpec(name="player", text="P", data={"player_id": PathNode(path="item.id")}),
        )
        buttons = await evaluate_value([node], scope)
        assert [b.data["player_id"] for b in buttons] == [10, 20]


class TestMediaItemNode:
    async def test_photo_with_spoiler(self, make_scope):
        scope = make_scope(data={"file": "id1"})
        node = MediaItemNode(media_type="photo", media=PathNode(path="data.file"), caption="cap", has_spoiler=True)
        media = await node.evaluate(scope)
        assert isinstance(media, InputMediaPhoto)
        assert media.media == "id1"
        assert media.caption == "cap"
        assert media.has_spoiler is True

    async def test_document_has_no_spoiler_field(self, scope):
        node = MediaItemNode(media_type="document", media="doc1")
        media = await node.evaluate(scope)
        assert isinstance(media, InputMediaDocument)
        assert media.media == "doc1"
