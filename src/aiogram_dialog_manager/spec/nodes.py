"""Standard node kinds: the expression language and structural constructs.

Every node here is registered through the same public :data:`node_registry`
mechanism that user-defined node kinds use (dogfooding by design).
"""
import inspect
import operator
from typing import Any, Literal, Optional

from aiogram.types import InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo
from pydantic import Field, model_serializer, model_validator

from aiogram_dialog_manager.instance.button import (
    ButtonInstance,
    CommonButtonAdditionalParameters,
    InlineButtonAdditionalParameters,
)
from aiogram_dialog_manager.spec.errors import ExpressionEvaluationError, UnknownReferenceError
from aiogram_dialog_manager.spec.node import (
    OMIT,
    EvaluableNode,
    Spliced,
    Value,
    evaluate_value,
    node_registry,
    render_into,
)
from aiogram_dialog_manager.spec.scope import EvalScope

# A normal identifier, optionally followed by a ``#N`` auto-name marker. The
# suffix is only ever produced by the textual DSL for anonymous declarations
# (windows/buttons nobody references); ``#`` cannot start or appear mid-name, so
# hand-written names stay strict and the marker unambiguously flags auto-names.
IDENTIFIER_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*(#[0-9]+)?$"

_EVALUATION_ERRORS = (TypeError, ValueError, KeyError, IndexError, AttributeError, ZeroDivisionError)


@node_registry.register
class LiteralNode(EvaluableNode):
    """Escape hatch: returns ``value`` verbatim.

    Needed for literal dicts that themselves contain a ``"type"`` key, which
    would otherwise be resolved as a node.
    """

    type: Literal["literal"] = "literal"
    value: Any = None

    async def evaluate(self, scope: EvalScope) -> Any:
        return self.value


@node_registry.register
class EscapeNode(EvaluableNode):
    """A plain object whose key set may include ``"type"``.

    A dict with a ``"type"`` key placed in a ``Value`` field is otherwise taken
    for a node. This wraps such a map so the **container** is kept as data while
    its values are still evaluated — unlike ``literal``, which freezes the whole
    subtree. Only this one level is escaped; the values stay ordinary
    expressions.
    """

    type: Literal["escape"] = "escape"
    entries: dict[str, Value] = Field(default_factory=dict)

    async def evaluate(self, scope: EvalScope) -> dict:
        return {key: await evaluate_value(value, scope) for key, value in self.entries.items()}


@node_registry.register
class PathNode(EvaluableNode):
    """Reads a dotted path from an explicit namespace: ``data.*``, ``ctx.*``
    or a construct-local name (``item``, ``index``). Missing path -> ``None``."""

    type: Literal["path"] = "path"
    path: str = Field(..., min_length=1)

    async def evaluate(self, scope: EvalScope) -> Any:
        return scope.resolve_path(self.path)


_BINARY_OPERATORS = {
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "%": operator.mod,
    "in": lambda a, b: a in b,
    "not in": lambda a, b: a not in b,
}

OperatorName = Literal[
    "<", ">", "<=", ">=", "==", "!=", "+", "-", "*", "/", "%", "in", "not in", "and", "or", "not",
]


@node_registry.register
class OpNode(EvaluableNode):
    """An operator application.

    ``and``/``or`` have Python semantics: short circuit, return an operand
    (useful for defaults: ``data.name or "anonymous"``). Type errors and
    division by zero raise — a silent ``None`` would hide script bugs.
    """

    type: Literal["op"] = "op"
    op: OperatorName
    args: list[Value]

    @model_validator(mode="after")
    def _check_arity(self) -> "OpNode":
        if self.op == "not":
            expected = 1
        elif self.op in ("and", "or"):
            if len(self.args) < 2:
                raise ValueError(f"Operator '{self.op}' requires at least 2 arguments, got {len(self.args)}")
            return self
        else:
            expected = 2
        if len(self.args) != expected:
            raise ValueError(f"Operator '{self.op}' requires exactly {expected} argument(s), got {len(self.args)}")
        return self

    async def evaluate(self, scope: EvalScope) -> Any:
        if self.op == "not":
            return not await evaluate_value(self.args[0], scope)
        if self.op in ("and", "or"):
            stop_on_truthy = self.op == "or"
            result: Any = None
            for arg in self.args:
                result = await evaluate_value(arg, scope)
                if bool(result) == stop_on_truthy:
                    return result
            return result
        left = await evaluate_value(self.args[0], scope)
        right = await evaluate_value(self.args[1], scope)
        try:
            return _BINARY_OPERATORS[self.op](left, right)
        except _EVALUATION_ERRORS as exc:
            raise ExpressionEvaluationError(f"Operator '{self.op}' failed: {exc}") from exc


@node_registry.register
class CallNode(EvaluableNode):
    """Calls a pure function from the function registry."""

    type: Literal["call"] = "call"
    name: str = Field(..., min_length=1)
    args: list[Value] = Field(default_factory=list)
    kwargs: dict[str, Value] = Field(default_factory=dict)

    async def evaluate(self, scope: EvalScope) -> Any:
        func = scope.runtime.functions.get(self.name)
        args = [await evaluate_value(arg, scope) for arg in self.args]
        kwargs = {key: await evaluate_value(arg, scope) for key, arg in self.kwargs.items()}
        try:
            return func(*args, **kwargs)
        except _EVALUATION_ERRORS as exc:
            raise ExpressionEvaluationError(f"Function '{self.name}' failed: {exc}") from exc


@node_registry.register
class TranslateNode(EvaluableNode):
    """A translatable string: ``{"type": "t", "key": "welcome_text"}``.

    Rendered through the optional ``translator(msgid, locale)`` hook; the
    locale comes from the render context (``ctx.locale``). Without a
    translator the msgid is returned as is.
    """

    type: Literal["t"] = "t"
    key: str = Field(..., min_length=1)

    async def evaluate(self, scope: EvalScope) -> str:
        translator = scope.runtime.translator
        if translator is None:
            return self.key
        return translator(self.key, scope.context.get("locale"))


@node_registry.register
class FormatNode(EvaluableNode):
    """String interpolation via ``str.format``.

    Fills ``{name}`` / ``{0}`` placeholders of ``template`` with the evaluated
    ``args`` (positional) and ``kwargs`` (named). ``template`` is itself a
    :data:`Value` — most usefully a ``t`` node — so a translated msgid carrying
    ``{placeholders}`` becomes directly fillable, closing the gap where ``t``
    returns the msgid verbatim (fragment lists and DSL ``${...}`` holes cover
    the concatenation case; this covers the single-template case).
    """

    type: Literal["format"] = "format"
    template: Value
    args: list[Value] = Field(default_factory=list)
    kwargs: dict[str, Value] = Field(default_factory=dict)

    async def evaluate(self, scope: EvalScope) -> Optional[str]:
        template = await evaluate_value(self.template, scope)
        if template is None:
            return None
        args = [await evaluate_value(arg, scope) for arg in self.args]
        kwargs = {key: await evaluate_value(arg, scope) for key, arg in self.kwargs.items()}
        try:
            return str(template).format(*args, **kwargs)
        except _EVALUATION_ERRORS as exc:
            raise ExpressionEvaluationError(f"'format' failed: {exc}") from exc


@node_registry.register
class ProviderNode(EvaluableNode):
    """The escape hatch for external data: evaluated by a named Python
    provider ``(dialog, context, **kwargs)`` from the provider registry."""

    type: Literal["provider"] = "provider"
    name: str = Field(..., min_length=1)
    args: dict[str, Value] = Field(default_factory=dict)

    async def evaluate(self, scope: EvalScope) -> Any:
        provider = scope.runtime.providers.get(self.name)
        kwargs = {key: await evaluate_value(arg, scope) for key, arg in self.args.items()}
        result = provider(scope.dialog, scope.context, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result


@node_registry.register
class RefNode(EvaluableNode):
    """A reference to a named reusable fragment from the dialog's ``defs``."""

    type: Literal["ref"] = "ref"
    name: str = Field(..., min_length=1)

    async def evaluate(self, scope: EvalScope) -> Any:
        if self.name not in scope.runtime.defs:
            raise UnknownReferenceError(f"Reference '{self.name}' is not present in defs")
        target = scope.runtime.defs[self.name]
        if isinstance(target, EvaluableNode):
            return await target.evaluate(scope)
        return await evaluate_value(target, scope)


@node_registry.register
class IfNode(EvaluableNode):
    """Conditional inclusion of a node (button, row, text fragment, menu part).

    Without an ``else`` branch a failed condition yields nothing: the node is
    dropped in list contexts and becomes ``None`` in value contexts.
    """

    type: Literal["if"] = "if"
    when: Value
    then: Value = None
    else_: Value = Field(default=None, alias="else")

    model_config = EvaluableNode.model_config | {"populate_by_name": True}

    @model_serializer(mode="wrap")
    def _drop_unset_else(self, handler):
        # The canonical form distinguishes "no else" (key absent) from
        # "else: null" — mirror that distinction when serializing.
        data = handler(self)
        if "else_" not in self.model_fields_set:
            data.pop("else", None)
            data.pop("else_", None)
        return data

    async def evaluate(self, scope: EvalScope) -> Any:
        if await evaluate_value(self.when, scope):
            return await self._branch(self.then, scope)
        if "else_" in self.model_fields_set:
            return await self._branch(self.else_, scope)
        return OMIT

    @staticmethod
    async def _branch(value: Value, scope: EvalScope) -> Any:
        # A branch may itself be a splicing node (e.g. foreach) — propagate.
        if isinstance(value, EvaluableNode):
            return await value.evaluate(scope)
        return await evaluate_value(value, scope)


@node_registry.register
class ForeachNode(EvaluableNode):
    """Multiplies a node over a list: ``over`` -> list, local scope gets
    ``item``/``index``. The results are spliced into the enclosing list."""

    type: Literal["foreach"] = "foreach"
    over: Value
    body: Value
    #: Optional aliases for the element/index (textual DSL ``foreach x, i in ...``).
    #: ``item``/``index`` stay bound as defaults; aliases are bound in addition,
    #: so a nested ``foreach`` with distinct aliases can still reach the outer
    #: element (grammar decision D10).
    var: Optional[str] = None
    index_var: Optional[str] = None

    async def evaluate(self, scope: EvalScope) -> Spliced:
        items = await evaluate_value(self.over, scope)
        if not isinstance(items, list):
            raise ExpressionEvaluationError(
                f"'foreach' expects 'over' to evaluate to a list, got {type(items).__name__}"
            )
        rendered: list = []
        for index, item in enumerate(items):
            local: dict[str, Any] = {"item": item, "index": index}
            if self.var is not None:
                local[self.var] = item
            if self.index_var is not None:
                local[self.index_var] = index
            await render_into(rendered, self.body, scope.child(**local))
        return Spliced(rendered)


@node_registry.register
class ChunkNode(EvaluableNode):
    """Lays out a flat list of items into rows of ``size`` (button grids)."""

    type: Literal["chunk"] = "chunk"
    size: Value
    items: list[Value]

    async def evaluate(self, scope: EvalScope) -> Spliced:
        size = await evaluate_value(self.size, scope)
        if not isinstance(size, int) or isinstance(size, bool) or size < 1:
            raise ExpressionEvaluationError(f"'chunk' size must be a positive integer, got {size!r}")
        flat: list = []
        for item in self.items:
            await render_into(flat, item, scope)
        return Spliced([flat[i:i + size] for i in range(0, len(flat), size)])


@node_registry.register
class SliceNode(EvaluableNode):
    """A list slice with expression bounds; with ``foreach`` covers pagination."""

    type: Literal["slice"] = "slice"
    over: Value
    start: Value = None
    stop: Value = None

    async def evaluate(self, scope: EvalScope) -> list:
        items = await evaluate_value(self.over, scope)
        if not isinstance(items, list):
            raise ExpressionEvaluationError(
                f"'slice' expects 'over' to evaluate to a list, got {type(items).__name__}"
            )
        start = await evaluate_value(self.start, scope)
        stop = await evaluate_value(self.stop, scope)
        try:
            return items[start:stop]
        except _EVALUATION_ERRORS as exc:
            raise ExpressionEvaluationError(f"'slice' failed: {exc}") from exc


@node_registry.register
class RowNode(EvaluableNode):
    """An explicit row of buttons; items are rendered with splice semantics."""

    type: Literal["row"] = "row"
    items: list[Value]

    async def evaluate(self, scope: EvalScope) -> list:
        rendered: list = []
        for item in self.items:
            await render_into(rendered, item, scope)
        return rendered


@node_registry.register
class ButtonSpec(EvaluableNode):
    """A declarative button.

    ``data`` is the payload channel to handlers: a dict whose values are
    expressions (literals are a special case), evaluated at render time —
    inside ``foreach`` each button carries its own item's values.

    ``inline``/``common`` mirror the existing ``ButtonInstance`` additional
    parameter models; string values may be expressions (dynamic urls, ...).
    """

    type: Literal["button"] = "button"
    name: str = Field(..., pattern=IDENTIFIER_PATTERN)
    text: Value
    data: dict[str, Value] = Field(default_factory=dict)
    inline: Optional[dict[str, Value]] = None
    common: Optional[dict[str, Value]] = None

    def type_name(self, scope: EvalScope) -> str:
        parts = [scope.runtime.dialog_name, scope.window_name, self.name]
        return ":".join(part for part in parts if part is not None)

    async def evaluate_text(self, scope: EvalScope) -> str:
        text = await evaluate_value(self.text, scope)
        if text is None:
            raise ExpressionEvaluationError(f"Text of button '{self.name}' evaluated to None")
        if isinstance(text, list):
            return "".join("" if fragment is None else str(fragment) for fragment in text)
        return str(text)

    async def evaluate_data(self, scope: EvalScope) -> dict:
        return {key: await evaluate_value(value, scope) for key, value in self.data.items()}

    async def evaluate_inline_parameters(self, scope: EvalScope) -> Optional[InlineButtonAdditionalParameters]:
        if self.inline is None:
            return None
        return InlineButtonAdditionalParameters.model_validate(await evaluate_value(self.inline, scope))

    async def evaluate_common_parameters(self, scope: EvalScope) -> Optional[CommonButtonAdditionalParameters]:
        if self.common is None:
            return None
        return CommonButtonAdditionalParameters.model_validate(await evaluate_value(self.common, scope))

    async def evaluate(self, scope: EvalScope) -> ButtonInstance:
        return ButtonInstance(
            text=await self.evaluate_text(scope),
            type_name=self.type_name(scope),
            data=await self.evaluate_data(scope),
            inline_additional_parameters=await self.evaluate_inline_parameters(scope),
            common_additional_parameters=await self.evaluate_common_parameters(scope),
        )


_MEDIA_ITEM_CLASSES = {
    "photo": InputMediaPhoto,
    "video": InputMediaVideo,
    "document": InputMediaDocument,
    "audio": InputMediaAudio,
}
_SPOILER_MEDIA_TYPES = ("photo", "video")


@node_registry.register
class MediaItemNode(EvaluableNode):
    """A single item of a media group; evaluates to an aiogram ``InputMedia*``."""

    type: Literal["media_item"] = "media_item"
    media_type: Literal["photo", "video", "document", "audio"]
    media: Value
    caption: Value = None
    has_spoiler: Value = None

    async def evaluate(self, scope: EvalScope):
        kwargs: dict[str, Any] = {
            "media": await evaluate_value(self.media, scope),
            "caption": await evaluate_value(self.caption, scope),
        }
        if self.media_type in _SPOILER_MEDIA_TYPES:
            kwargs["has_spoiler"] = await evaluate_value(self.has_spoiler, scope)
        return _MEDIA_ITEM_CLASSES[self.media_type](**kwargs)
