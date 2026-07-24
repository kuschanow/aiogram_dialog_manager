"""The ergonomic Python builder over the spec core.

The builder does not add semantics of its own: every function constructs core
model objects (IDE types and autocompletion included). Expressions are built
either explicitly (:func:`path`, :func:`fn`, ...) or through the operator
proxies ``data_``/``ctx_``/``item_``/``index_``::

    from aiogram_dialog_manager.spec import builder as b

    spec = b.dialog(
        "settings",
        windows={
            "main": b.window(
                b.text("Hello, ", b.fn("default", b.data_.name, "anonymous"), "!"),
                menu=b.menu(
                    b.row(b.button("save", b.t("save_btn"))),
                    b.foreach(b.data_.players, b.row(
                        b.button("player", b.item_.name, data={"player_id": b.item_.id}),
                    )),
                ),
            ),
        },
    )

Widgets (like :func:`paginator`) are builder-level macro patterns: they expand
into core primitives, the serialized model is always "unpacked" and the
interpreter knows nothing about them.
"""
from typing import Any, Optional, Union

from aiogram_dialog_manager.spec.model import DialogSpec, MenuSpec, WindowSpec
from aiogram_dialog_manager.spec.node import SpecNode
from aiogram_dialog_manager.spec.nodes import (
    ButtonSpec,
    CallNode,
    ChunkNode,
    EscapeNode,
    ForeachNode,
    IfNode,
    LiteralNode,
    MediaItemNode,
    OpNode,
    PathNode,
    ProviderNode,
    RefNode,
    RowNode,
    SliceNode,
    TranslateNode,
)
from aiogram_dialog_manager.spec.content import (
    DocumentContentSpec,
    MediaGroupContentSpec,
    PhotoContentSpec,
    TextContentSpec,
)
from aiogram_dialog_manager.spec.use import UseButtonNode, UseMenuNode, UseMessageContentSpec

_UNSET = object()


class Expr:
    """A thin wrapper turning Python operators into expression nodes.

    Unwrapped automatically by model validation (via ``__spec_node__``), so an
    ``Expr`` can be passed anywhere a spec value is expected.

    Note: ``==``/``!=`` build nodes instead of comparing — do not use ``Expr``
    objects as dict keys or in equality assertions.
    """

    __slots__ = ("_node",)

    def __init__(self, node: SpecNode):
        self._node = node

    def __spec_node__(self) -> SpecNode:
        return self._node

    def _binary(self, op: str, other: Any, *, reflected: bool = False) -> "Expr":
        args = [other, self] if reflected else [self, other]
        return Expr(OpNode(op=op, args=args))

    def __lt__(self, other): return self._binary("<", other)
    def __gt__(self, other): return self._binary(">", other)
    def __le__(self, other): return self._binary("<=", other)
    def __ge__(self, other): return self._binary(">=", other)
    def __eq__(self, other): return self._binary("==", other)
    def __ne__(self, other): return self._binary("!=", other)
    def __add__(self, other): return self._binary("+", other)
    def __radd__(self, other): return self._binary("+", other, reflected=True)
    def __sub__(self, other): return self._binary("-", other)
    def __rsub__(self, other): return self._binary("-", other, reflected=True)
    def __mul__(self, other): return self._binary("*", other)
    def __rmul__(self, other): return self._binary("*", other, reflected=True)
    def __truediv__(self, other): return self._binary("/", other)
    def __rtruediv__(self, other): return self._binary("/", other, reflected=True)
    def __mod__(self, other): return self._binary("%", other)
    def __rmod__(self, other): return self._binary("%", other, reflected=True)
    def __and__(self, other): return self._binary("and", other)
    def __or__(self, other): return self._binary("or", other)
    def __invert__(self): return Expr(OpNode(op="not", args=[self]))

    __hash__ = None


class PathExpr(Expr):
    """A data path with attribute-style extension: ``data_.players`` etc."""

    __slots__ = ()

    def __getattr__(self, name: str) -> "PathExpr":
        if name.startswith("_"):
            raise AttributeError(name)
        node: PathNode = self._node
        return PathExpr(PathNode(path=f"{node.path}.{name}"))

    def __getitem__(self, index: Union[int, str]) -> "PathExpr":
        node: PathNode = self._node
        return PathExpr(PathNode(path=f"{node.path}.{index}"))


def path(dotted_path: str) -> PathExpr:
    return PathExpr(PathNode(path=dotted_path))


#: Root namespace proxies.
data_ = path("data")
ctx_ = path("ctx")
item_ = path("item")
index_ = path("index")


def as_expr(value: Any) -> Expr:
    """Wrap a node (or an already-wrapped value) into an :class:`Expr`."""
    if isinstance(value, Expr):
        return value
    if isinstance(value, SpecNode):
        return Expr(value)
    return lit(value)


def lit(value: Any) -> Expr:
    """A verbatim literal (needed for dicts containing a ``"type"`` key)."""
    return Expr(LiteralNode(value=value))


def escape(entries: dict[str, Any]) -> Expr:
    """A plain object literal whose values are still evaluated — the shallow
    counterpart to :func:`lit`. Use it when a map's keys include ``"type"`` but
    some values are expressions: only the container is escaped, not the values.
    """
    return Expr(EscapeNode(entries=entries))


def fn(name: str, *args: Any, **kwargs: Any) -> Expr:
    return Expr(CallNode(name=name, args=list(args), kwargs=kwargs))


def t(key: str) -> Expr:
    return Expr(TranslateNode(key=key))


def provider(name: str, **args: Any) -> Expr:
    return Expr(ProviderNode(name=name, args=args))


def ref(name: str) -> Expr:
    return Expr(RefNode(name=name))


def and_(*args: Any) -> Expr:
    return Expr(OpNode(op="and", args=list(args)))


def or_(*args: Any) -> Expr:
    return Expr(OpNode(op="or", args=list(args)))


def not_(value: Any) -> Expr:
    return Expr(OpNode(op="not", args=[value]))


def in_(needle: Any, haystack: Any) -> Expr:
    return Expr(OpNode(op="in", args=[needle, haystack]))


def not_in(needle: Any, haystack: Any) -> Expr:
    return Expr(OpNode(op="not in", args=[needle, haystack]))


def if_(when: Any, then: Any, else_: Any = _UNSET) -> IfNode:
    if else_ is _UNSET:
        return IfNode(when=when, then=then)
    return IfNode(when=when, then=then, else_=else_)


def foreach(over: Any, body: Any, *, var: Optional[str] = None, index_var: Optional[str] = None) -> ForeachNode:
    """Iterate ``over``, splicing ``body`` per element. ``item``/``index`` are
    always bound; ``var``/``index_var`` add aliases (so a nested ``foreach`` can
    still reach the outer element)."""
    return ForeachNode(over=over, body=body, var=var, index_var=index_var)


def chunk(size: Any, *items: Any) -> ChunkNode:
    return ChunkNode(size=size, items=list(items))


def slice_(over: Any, start: Any = None, stop: Any = None) -> SliceNode:
    return SliceNode(over=over, start=start, stop=stop)


def row(*items: Any) -> RowNode:
    return RowNode(items=list(items))


def button(
        name: str, text: Any, *,
        data: Optional[dict[str, Any]] = None,
        inline: Optional[dict[str, Any]] = None,
        common: Optional[dict[str, Any]] = None,
) -> ButtonSpec:
    return ButtonSpec(name=name, text=text, data=data or {}, inline=inline, common=common)


def menu(
        *rows: Any,
        keyboard_type: str = "inline",
        reply_parameters: Optional[dict[str, Any]] = None,
) -> MenuSpec:
    return MenuSpec(rows=list(rows), keyboard_type=keyboard_type, reply_parameters=reply_parameters)


def use_button(name: str, *, context: Optional[dict[str, Any]] = None) -> UseButtonNode:
    """Render an existing registered button prototype (it keeps its own
    ``type_name``, so its handlers keep working). ``context`` values are
    expressions merged over the render context."""
    return UseButtonNode(name=name, context=context)


def use_menu(name: str, *, context: Optional[dict[str, Any]] = None) -> UseMenuNode:
    """Delegate the window's menu to an existing registered menu prototype."""
    return UseMenuNode(name=name, context=context)


def use_message(name: str) -> UseMessageContentSpec:
    """Delegate the window's message to an existing registered message
    prototype (such a window declares neither ``menu`` nor ``data``)."""
    return UseMessageContentSpec(name=name)


def text(*fragments: Any) -> TextContentSpec:
    return TextContentSpec(text=fragments[0] if len(fragments) == 1 else list(fragments))


def photo(media: Any, caption: Any = None, *, has_spoiler: Any = None, show_caption_above_media: Any = None) -> PhotoContentSpec:
    return PhotoContentSpec(
        photo=media, caption=caption,
        has_spoiler=has_spoiler, show_caption_above_media=show_caption_above_media,
    )


def document(media: Any, caption: Any = None, *, disable_content_type_detection: Any = None) -> DocumentContentSpec:
    return DocumentContentSpec(
        document=media, caption=caption,
        disable_content_type_detection=disable_content_type_detection,
    )


def media_item(media_type: str, media: Any, caption: Any = None, *, has_spoiler: Any = None) -> MediaItemNode:
    return MediaItemNode(media_type=media_type, media=media, caption=caption, has_spoiler=has_spoiler)


def media_group(*items: Any) -> MediaGroupContentSpec:
    return MediaGroupContentSpec(items=list(items))


def window(
        content: Any,
        menu: Optional[Union[MenuSpec, UseMenuNode]] = None,
        *,
        data: Optional[dict[str, Any]] = None,
) -> WindowSpec:
    return WindowSpec(content=content, menu=menu, data=data)


def dialog(
        name: str, *,
        windows: dict[str, WindowSpec],
        defs: Optional[dict[str, Any]] = None,
        window_name_key: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
        config: Optional[dict[str, Any]] = None,
        version: int = 1,
) -> DialogSpec:
    return DialogSpec(
        version=version, name=name, windows=windows, defs=defs or {},
        window_name_key=window_name_key, data=data, config=config,
    )


def paginator(
        name: str, *,
        over: Any,
        page: Any,
        item: Any,
        page_size: int = 5,
        per_row: int = 1,
        prev_text: Any = "«",
        next_text: Any = "»",
) -> list[Any]:
    """A pagination widget: expands into ``slice`` + ``foreach`` + a nav row.

    Returns row-level values to be passed into :func:`menu`. The nav buttons
    are named ``{name}_prev``/``{name}_next`` and carry ``{"page": <target>}``
    in their payload — handle them with ``ButtonFilter`` and re-render.
    """
    page = as_expr(page)
    page_items = slice_(over, start=page * page_size, stop=(page + 1) * page_size)
    has_next = (page + 1) * page_size < fn("len", over)
    has_prev = page > 0
    return [
        chunk(per_row, foreach(page_items, item)),
        row(
            if_(has_prev, button(f"{name}_prev", prev_text, data={"page": page - 1})),
            if_(has_next, button(f"{name}_next", next_text, data={"page": page + 1})),
        ),
    ]
