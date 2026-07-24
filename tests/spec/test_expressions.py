"""Tests for the expression language: paths, operators, calls, t, provider, ref."""
import pytest

from aiogram_dialog_manager.spec import (
    CallNode,
    ExpressionEvaluationError,
    FormatNode,
    LiteralNode,
    OpNode,
    PathNode,
    ProviderNode,
    RefNode,
    SpecNode,
    TranslateNode,
    UnknownFunctionError,
    UnknownProviderError,
    UnknownReferenceError,
    evaluate_value,
    node_registry,
    resolve_value,
)
from aiogram_dialog_manager.spec.registries import ProviderRegistry


class TestResolveValue:
    def test_scalars_pass_through(self):
        assert resolve_value(5) == 5
        assert resolve_value("x") == "x"
        assert resolve_value(None) is None

    def test_node_dict_resolved(self):
        node = resolve_value({"type": "path", "path": "data.x"})
        assert isinstance(node, PathNode)

    def test_node_instance_passes_through(self):
        node = PathNode(path="data.x")
        assert resolve_value(node) is node

    def test_plain_dict_resolved_recursively(self):
        result = resolve_value({"key": {"type": "path", "path": "data.x"}})
        assert isinstance(result["key"], PathNode)

    def test_list_and_tuple_resolved(self):
        result = resolve_value(("a", {"type": "path", "path": "data.x"}))
        assert isinstance(result, list)
        assert isinstance(result[1], PathNode)

    def test_spec_node_protocol_unwrapped(self):
        class Wrapper:
            def __spec_node__(self):
                return PathNode(path="data.x")

        assert isinstance(resolve_value(Wrapper()), PathNode)


class TestEvaluateValue:
    async def test_literal_scalars(self, scope):
        assert await evaluate_value(42, scope) == 42
        assert await evaluate_value("hi", scope) == "hi"

    async def test_dict_values_evaluated(self, make_scope):
        scope = make_scope(data={"x": 7})
        result = await evaluate_value({"key": PathNode(path="data.x")}, scope)
        assert result == {"key": 7}

    async def test_non_evaluable_node_raises(self, scope):
        class Inert(SpecNode):
            type: str = "inert"

        with pytest.raises(ExpressionEvaluationError, match="not evaluable"):
            await evaluate_value(Inert(), scope)

    async def test_literal_node_returns_value_verbatim(self, scope):
        node = LiteralNode(value={"type": "not_a_node"})
        assert await evaluate_value(node, scope) == {"type": "not_a_node"}


class TestPathNode:
    async def test_data_namespace(self, make_scope):
        scope = make_scope(data={"page": 3})
        assert await PathNode(path="data.page").evaluate(scope) == 3

    async def test_data_without_dialog_is_empty(self, make_scope):
        scope = make_scope()
        assert await PathNode(path="data.page").evaluate(scope) is None

    async def test_ctx_namespace(self, make_scope):
        scope = make_scope(context={"locale": "ru"})
        assert await PathNode(path="ctx.locale").evaluate(scope) == "ru"

    async def test_local_namespace(self, make_scope):
        scope = make_scope(locals_={"item": {"id": 1}, "index": 0})
        assert await PathNode(path="item.id").evaluate(scope) == 1
        assert await PathNode(path="index").evaluate(scope) == 0

    async def test_missing_path_is_none(self, make_scope):
        scope = make_scope(data={"a": {"b": 1}})
        assert await PathNode(path="data.a.c").evaluate(scope) is None
        assert await PathNode(path="data.missing.deep").evaluate(scope) is None
        assert await PathNode(path="unknown_root.x").evaluate(scope) is None

    async def test_list_indexing(self, make_scope):
        scope = make_scope(data={"items": ["a", "b", "c"]})
        assert await PathNode(path="data.items.1").evaluate(scope) == "b"
        assert await PathNode(path="data.items.-1").evaluate(scope) == "c"
        assert await PathNode(path="data.items.9").evaluate(scope) is None

    async def test_traversing_scalar_raises(self, make_scope):
        scope = make_scope(data={"n": 5})
        with pytest.raises(ExpressionEvaluationError, match="not traversable"):
            await PathNode(path="data.n.x").evaluate(scope)


class TestOpNode:
    @pytest.mark.parametrize("op,args,expected", [
        ("<", [1, 2], True),
        (">", [1, 2], False),
        ("<=", [2, 2], True),
        (">=", [1, 2], False),
        ("==", [2, 2], True),
        ("!=", [2, 2], False),
        ("+", [2, 3], 5),
        ("-", [5, 3], 2),
        ("*", [2, 3], 6),
        ("/", [7, 2], 3.5),
        ("%", [7, 2], 1),
        ("in", [1, [1, 2]], True),
        ("not in", [3, [1, 2]], True),
    ])
    async def test_binary_operators(self, scope, op, args, expected):
        assert await OpNode(op=op, args=args).evaluate(scope) == expected

    async def test_and_returns_operand(self, make_scope):
        scope = make_scope(data={"name": "Roman"})
        node = OpNode(op="and", args=[True, PathNode(path="data.name")])
        assert await node.evaluate(scope) == "Roman"

    async def test_or_returns_first_truthy(self, make_scope):
        scope = make_scope(data={})
        node = OpNode(op="or", args=[PathNode(path="data.name"), "anonymous"])
        assert await node.evaluate(scope) == "anonymous"

    async def test_and_short_circuits(self, scope):
        # The failing division is never evaluated.
        node = OpNode(op="and", args=[False, OpNode(op="/", args=[1, 0])])
        assert await node.evaluate(scope) is False

    async def test_or_short_circuits(self, scope):
        node = OpNode(op="or", args=["value", OpNode(op="/", args=[1, 0])])
        assert await node.evaluate(scope) == "value"

    async def test_not(self, scope):
        assert await OpNode(op="not", args=[0]).evaluate(scope) is True
        assert await OpNode(op="not", args=["x"]).evaluate(scope) is False

    async def test_division_by_zero_raises(self, scope):
        with pytest.raises(ExpressionEvaluationError, match="Operator '/' failed"):
            await OpNode(op="/", args=[1, 0]).evaluate(scope)

    async def test_type_error_raises(self, scope):
        with pytest.raises(ExpressionEvaluationError, match="Operator '\\+' failed"):
            await OpNode(op="+", args=[1, "x"]).evaluate(scope)

    def test_binary_arity_validated(self):
        with pytest.raises(ValueError, match="exactly 2"):
            OpNode(op="+", args=[1])

    def test_not_arity_validated(self):
        with pytest.raises(ValueError, match="exactly 1"):
            OpNode(op="not", args=[1, 2])

    def test_and_arity_validated(self):
        with pytest.raises(ValueError, match="at least 2"):
            OpNode(op="and", args=[1])


class TestCallNode:
    async def test_call_with_args_and_kwargs(self, scope):
        node = CallNode(name="round", args=[3.14159], kwargs={"ndigits": 2})
        assert await node.evaluate(scope) == 3.14

    async def test_unknown_function_raises(self, scope):
        with pytest.raises(UnknownFunctionError):
            await CallNode(name="nope").evaluate(scope)

    async def test_function_error_wrapped(self, scope):
        with pytest.raises(ExpressionEvaluationError, match="Function 'int' failed"):
            await CallNode(name="int", args=["not a number"]).evaluate(scope)

    @pytest.mark.parametrize("name,args,expected", [
        ("len", [[1, 2, 3]], 3),
        ("str", [5], "5"),
        ("int", ["7"], 7),
        ("float", ["1.5"], 1.5),
        ("bool", [0], False),
        ("round", [2.7], 3),
        ("abs", [-4], 4),
        ("min", [3, 1], 1),
        ("max", [3, 1], 3),
        ("sum", [[1, 2, 3]], 6),
        ("join", [["a", "b"], ", "], "a, b"),
        ("join", [[1, 2]], "12"),
        ("split", ["a b"], ["a", "b"]),
        ("split", ["a,b", ","], ["a", "b"]),
        ("upper", ["ab"], "AB"),
        ("lower", ["AB"], "ab"),
        ("strip", ["  x  "], "x"),
        ("strip", ["--x--", "-"], "x"),
        ("format", ["{}: {v}", "a"], None),  # placeholder, checked below
        ("default", [None, "d"], "d"),
        ("default", ["v", "d"], "v"),
        ("range", [3], [0, 1, 2]),
        ("range", [1, 4], [1, 2, 3]),
        ("sorted", [[3, 1, 2]], [1, 2, 3]),
        ("keys", [{"a": 1}], ["a"]),
        ("values", [{"a": 1}], [1]),
    ])
    async def test_starter_functions(self, scope, name, args, expected):
        if name == "format":
            node = CallNode(name="format", args=["{}: {v}", "a"], kwargs={"v": 1})
            assert await node.evaluate(scope) == "a: 1"
            return
        assert await CallNode(name=name, args=args).evaluate(scope) == expected

    async def test_sorted_reverse(self, scope):
        node = CallNode(name="sorted", args=[[1, 3, 2]], kwargs={"reverse": True})
        assert await node.evaluate(scope) == [3, 2, 1]


class TestTranslateNode:
    async def test_without_translator_returns_key(self, make_scope):
        scope = make_scope()
        assert await TranslateNode(key="welcome").evaluate(scope) == "welcome"

    async def test_with_translator_uses_context_locale(self, make_scope):
        seen = {}

        def translator(msgid, locale):
            seen["args"] = (msgid, locale)
            return f"[{msgid}:{locale}]"

        scope = make_scope(translator=translator, context={"locale": "ru"})
        assert await TranslateNode(key="welcome").evaluate(scope) == "[welcome:ru]"
        assert seen["args"] == ("welcome", "ru")

    async def test_with_translator_without_locale(self, make_scope):
        scope = make_scope(translator=lambda msgid, locale: f"{msgid}/{locale}")
        assert await TranslateNode(key="k").evaluate(scope) == "k/None"


class TestFormatNode:
    async def test_named_placeholders(self, make_scope):
        scope = make_scope(data={"name": "Roman"})
        node = FormatNode(template="Hi, {name}!", kwargs={"name": PathNode(path="data.name")})
        assert await node.evaluate(scope) == "Hi, Roman!"

    async def test_positional_placeholders(self, make_scope):
        scope = make_scope(data={"n": 3})
        node = FormatNode(template="{0}/{1}", args=[PathNode(path="data.n"), 10])
        assert await node.evaluate(scope) == "3/10"

    async def test_template_is_a_value_translated_msgid(self, make_scope):
        scope = make_scope(translator=lambda msgid, locale: "Привет, {name}", context={"locale": "ru"})
        node = FormatNode(template=TranslateNode(key="greeting"), kwargs={"name": "Роман"})
        assert await node.evaluate(scope) == "Привет, Роман"

    async def test_none_template_returns_none(self, make_scope):
        scope = make_scope()
        node = FormatNode(template=LiteralNode(value=None), kwargs={"x": 1})
        assert await node.evaluate(scope) is None

    async def test_missing_placeholder_wrapped(self, make_scope):
        scope = make_scope()
        node = FormatNode(template="{missing}")
        with pytest.raises(ExpressionEvaluationError, match="'format' failed"):
            await node.evaluate(scope)


class TestProviderNode:
    async def test_sync_provider(self, make_scope):
        providers = ProviderRegistry({"top": lambda dialog, context, limit: list(range(limit))})
        scope = make_scope(providers=providers)
        node = ProviderNode(name="top", args={"limit": 3})
        assert await node.evaluate(scope) == [0, 1, 2]

    async def test_async_provider_receives_dialog_and_context(self, make_scope):
        async def prov(dialog, context):
            return (dialog.data["x"], context["y"])

        scope = make_scope(data={"x": 1}, context={"y": 2}, providers=ProviderRegistry({"prov": prov}))
        assert await ProviderNode(name="prov").evaluate(scope) == (1, 2)

    async def test_unknown_provider_raises(self, scope):
        with pytest.raises(UnknownProviderError):
            await ProviderNode(name="ghost").evaluate(scope)


class TestRefNode:
    async def test_ref_to_node(self, make_scope):
        scope = make_scope(data={"x": 5}, defs={"val": PathNode(path="data.x")})
        assert await RefNode(name="val").evaluate(scope) == 5

    async def test_ref_to_plain_value(self, make_scope):
        scope = make_scope(defs={"val": [1, 2]})
        assert await RefNode(name="val").evaluate(scope) == [1, 2]

    async def test_unknown_ref_raises(self, scope):
        with pytest.raises(UnknownReferenceError, match="'ghost' is not present in defs"):
            await RefNode(name="ghost").evaluate(scope)


class TestNodeRegistryContents:
    @pytest.mark.parametrize("type_name", [
        "literal", "path", "op", "call", "t", "provider", "ref",
        "if", "foreach", "chunk", "slice", "row", "button", "media_item",
        "text", "photo", "document", "media_group",
    ])
    def test_standard_nodes_registered(self, type_name):
        assert type_name in node_registry
