"""Transform a langforge parse tree into the spec model (grammar D1-D20).

The tree is a CST; this pass builds the same objects the Python builder makes
(``DialogSpec`` / ``WindowSpec`` / nodes), so the result flows through the
existing ``compile_dialog`` unchanged.

Only two synthetic node kinds appear in the tree (the grammar uses no inline
groups/choices): ``_opt_*`` (from ``x?``) and ``_rep_*`` (from ``x*``); see
:func:`_opt` / :func:`_rep`.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from aiogram_dialog_manager.spec.content import (
    DocumentContentSpec,
    MediaGroupContentSpec,
    PhotoContentSpec,
    TextContentSpec,
)
from aiogram_dialog_manager.spec.model import DialogSpec, MenuSpec, WindowSpec
from aiogram_dialog_manager.spec.node import SpecNode, node_registry
from aiogram_dialog_manager.spec.nodes import (
    ButtonSpec,
    CallNode,
    ChunkNode,
    EscapeNode,
    ForeachNode,
    IfNode,
    MediaItemNode,
    OpNode,
    PathNode,
    ProviderNode,
    RefNode,
    RowNode,
    SliceNode,
    TranslateNode,
)
from aiogram_dialog_manager.spec.text.errors import DSLSyntaxError
from aiogram_dialog_manager.spec.text.strings import parse_string
from aiogram_dialog_manager.spec.use import UseButtonNode, UseMenuNode, UseMessageContentSpec

# Content field names -> which content spec they belong to.
_PRIMARY_CONTENT = {"text", "photo", "document"}
_PHOTO_SATELLITES = {"caption", "has_spoiler", "show_caption_above_media"}
_DOCUMENT_SATELLITES = {"caption", "disable_content_type_detection"}
_MEDIA_TYPES = {"photo", "video", "document", "audio"}


# Node shape comes from the generated parser: a terminal has ``terminal_name`` /
# ``token_value`` / ``position``; a nonterminal has ``name`` / ``children``.
def _is_term(node: Any) -> bool:
    return hasattr(node, "terminal_name")


def _name(node: Any) -> str:
    return node.terminal_name if _is_term(node) else node.name


def _tv(node: Any) -> str:
    return node.token_value


def _pos(node: Any) -> tuple[Optional[int], Optional[int]]:
    if _is_term(node):
        p = node.position
        return (getattr(p, "line", None), getattr(p, "col", None)) if p else (None, None)
    for child in node.children:
        pos = _pos(child)
        if pos != (None, None):
            return pos
    return (None, None)  # pragma: no cover - every node reaches a terminal


def _opt(node: Any) -> Optional[Any]:
    """Unwrap an ``x?`` node: its single child or ``None``."""
    return node.children[0] if node.children else None


def _rep(node: Any) -> list[Any]:
    """Flatten an ``x*`` right-recursive ``_rep`` chain into a list of items."""
    out: list[Any] = []
    while node.children:
        out.append(node.children[0])
        node = node.children[1]
    return out


def _err(node: Any, message: str) -> DSLSyntaxError:
    line, col = _pos(node)
    return DSLSyntaxError(message, line=line, col=col)


class Transformer:
    """Builds a :class:`DialogSpec` from a ``file`` parse tree."""

    def __init__(self, parse_expr_text: Callable[[str], SpecNode]):
        # Used for string-interpolation holes (re-parsed as expressions).
        self._parse_expr_text = parse_expr_text
        self._btn_counter = 0

    # ── entry ────────────────────────────────────────────────────────────
    def build(self, file_node: Any) -> DialogSpec:
        dialog_node = file_node.children[0]
        return self._dialog(dialog_node)

    # ── dialog ───────────────────────────────────────────────────────────
    def _dialog(self, node: Any) -> DialogSpec:
        # DIALOG IDENT? map? LBRACE dialog_member* RBRACE
        _, name_opt, map_opt, _lb, members_rep, _rb = node.children
        name_node = _opt(name_opt)
        name = _tv(name_node) if name_node else None
        if name is None:
            raise _err(node, "dialog must have a name")
        settings = self._map(_opt(map_opt)) if _opt(map_opt) else {}

        windows: dict[str, WindowSpec] = {}
        defs: dict[str, Any] = {}
        win_index = 0
        for member in _rep(members_rep):
            child = member.children[0]
            if _name(child) == "defs_block":
                defs.update(self._defs_block(child))
            else:  # window
                self._btn_counter = 0
                wname, wspec = self._window(child, win_index)
                if wname in windows:
                    raise _err(child, f"duplicate window name '{wname}'")
                windows[wname] = wspec
                win_index += 1

        if not windows:
            raise _err(node, "dialog must declare at least one window")

        kwargs: dict[str, Any] = {"name": name, "windows": windows, "defs": defs}
        if "window_name_key" in settings:
            kwargs["window_name_key"] = self._literal_str(settings.pop("window_name_key"), node, "window_name_key")
        if "data" in settings:
            kwargs["data"] = self._map_value_to_dict(settings.pop("data"), node, "data")
        if "config" in settings:
            kwargs["config"] = self._map_value_to_dict(settings.pop("config"), node, "config")
        if "version" in settings:
            kwargs["version"] = self._literal_int(settings.pop("version"), node, "version")
        if settings:
            raise _err(node, f"unknown dialog setting(s): {', '.join(sorted(settings))}")
        return DialogSpec(**kwargs)

    # ── defs ─────────────────────────────────────────────────────────────
    def _defs_block(self, node: Any) -> dict[str, Any]:
        # DEFS LBRACE def_entry* RBRACE
        entries = _rep(node.children[2])
        out: dict[str, Any] = {}
        for entry in entries:  # def_entry -> IDENT COLON value
            key = _tv(entry.children[0])
            if key in out:
                raise _err(entry, f"duplicate def '{key}'")
            out[key] = self._value(entry.children[2])
        return out

    # ── window ───────────────────────────────────────────────────────────
    def _window(self, node: Any, index: int) -> tuple[str, WindowSpec]:
        # WINDOW IDENT? map? LBRACE window_member* RBRACE
        _, name_opt, map_opt, _lb, members_rep, _rb = node.children
        name_node = _opt(name_opt)
        name = _tv(name_node) if name_node else f"window#{index}"
        config = self._map(_opt(map_opt)) if _opt(map_opt) else {}

        fields: dict[str, Any] = {}
        media_groups: list[Any] = []
        menu: Any = None
        explicit_content: Any = None

        for member in _rep(members_rep):
            child = member.children[0]
            kind = _name(child)
            if kind == "field":
                fname = _tv(child.children[0])
                if fname in fields:
                    raise _err(child, f"duplicate field '{fname}'")
                fields[fname] = self._expr(child.children[2])
            elif kind == "media_group":
                media_groups.append(self._media_group(child))
            elif kind in ("menu_decl", "menu_ref"):
                if menu is not None:
                    raise _err(child, "window declares more than one menu")
                menu = self._menu(child)
            elif kind in ("message_decl", "message_ref"):
                if explicit_content is not None:
                    raise _err(child, "window declares more than one message")
                explicit_content = self._message(child)

        content = self._window_content(node, fields, media_groups, explicit_content)

        data = None
        message_name = None
        if "data" in config:
            data = self._map_value_to_dict(config.pop("data"), node, "data")
        if "message_name" in config:
            message_name = self._literal_str(config.pop("message_name"), node, "message_name")
        if "send_params" in config:
            send_params = self._map_value_to_dict(config.pop("send_params"), node, "send_params")
            if explicit_content is not None:
                # An explicit 'message' owns its own send params; the window map
                # would silently shadow or fight them.
                raise _err(node, "window sets send_params but declares an explicit 'message'; put send_params on the message")
            content.send_params = send_params
        if config:
            raise _err(node, f"unknown window setting(s): {', '.join(sorted(config))}")

        return name, WindowSpec(content=content, menu=menu, data=data, message_name=message_name)

    def _window_content(self, node: Any, fields: dict, media_groups: list, explicit: Any) -> Any:
        has_sugar = bool(fields) or bool(media_groups)
        if explicit is not None:
            if has_sugar:
                raise _err(node, "window mixes an explicit 'message' with inline content fields")
            return explicit
        if not has_sugar:
            raise _err(node, "window has no content (a 'text'/'photo'/... field, media group, or message)")
        return self._content_from_fields(node, fields, media_groups)

    # ── message ──────────────────────────────────────────────────────────
    def _message(self, node: Any) -> Any:
        kind = _name(node)
        if kind == "message_ref":  # MESSAGE LPAREN expr RPAREN
            name = self._literal_str(self._expr(node.children[2]), node, "message() name")
            return UseMessageContentSpec(name=name)
        # message_decl -> MESSAGE IDENT? map? LBRACE content_member* RBRACE
        _, _name_opt, map_opt, _lb, members_rep, _rb = node.children
        config = self._map(_opt(map_opt)) if _opt(map_opt) else {}
        send_params = None
        if "send_params" in config:
            send_params = self._map_value_to_dict(config.pop("send_params"), node, "send_params")
        if config:
            raise _err(node, f"unknown message setting(s): {', '.join(sorted(config))}")
        fields: dict[str, Any] = {}
        media_groups: list[Any] = []
        for member in _rep(members_rep):
            child = member.children[0]
            if _name(child) == "field":
                fname = _tv(child.children[0])
                if fname in fields:
                    raise _err(child, f"duplicate field '{fname}'")
                fields[fname] = self._expr(child.children[2])
            else:  # media_group
                media_groups.append(self._media_group(child))
        if not fields and not media_groups:
            raise _err(node, "message has no content")
        content = self._content_from_fields(node, fields, media_groups)
        if send_params is not None:
            content.send_params = send_params
        return content

    def _content_from_fields(self, node: Any, fields: dict, media_groups: list) -> Any:
        if media_groups:
            if len(media_groups) > 1:
                raise _err(node, "more than one media group in one message")
            if fields:
                raise _err(node, "media group cannot be combined with other content fields")
            return media_groups[0]

        primary = [f for f in fields if f in _PRIMARY_CONTENT]
        if not primary:
            raise _err(node, f"missing a primary content field ({', '.join(sorted(_PRIMARY_CONTENT))})")
        if len(primary) > 1:
            raise _err(node, f"more than one primary content field: {', '.join(primary)}")
        kind = primary[0]

        if kind == "text":
            extra = set(fields) - {"text"}
            if extra:
                raise _err(node, f"unexpected field(s) for text content: {', '.join(sorted(extra))}")
            return TextContentSpec(text=fields["text"])
        if kind == "photo":
            extra = set(fields) - {"photo"} - _PHOTO_SATELLITES
            if extra:
                raise _err(node, f"unexpected field(s) for photo content: {', '.join(sorted(extra))}")
            return PhotoContentSpec(
                photo=fields["photo"],
                caption=fields.get("caption"),
                has_spoiler=fields.get("has_spoiler"),
                show_caption_above_media=fields.get("show_caption_above_media"),
            )
        extra = set(fields) - {"document"} - _DOCUMENT_SATELLITES
        if extra:
            raise _err(node, f"unexpected field(s) for document content: {', '.join(sorted(extra))}")
        return DocumentContentSpec(
            document=fields["document"],
            caption=fields.get("caption"),
            disable_content_type_detection=fields.get("disable_content_type_detection"),
        )

    # ── menu ─────────────────────────────────────────────────────────────
    def _menu(self, node: Any) -> Any:
        kind = _name(node)
        if kind == "menu_ref":  # MENU LPAREN expr RPAREN
            name = self._literal_str(self._expr(node.children[2]), node, "menu() name")
            return UseMenuNode(name=name)
        # menu_decl -> MENU IDENT? map? LBRACE value* RBRACE
        _, _name_opt, map_opt, _lb, values_rep, _rb = node.children
        config = self._map(_opt(map_opt)) if _opt(map_opt) else {}
        rows = [self._value(v) for v in _rep(values_rep)]
        kwargs: dict[str, Any] = {"rows": rows}
        if "keyboard_type" in config:
            kwargs["keyboard_type"] = self._literal_str(config.pop("keyboard_type"), node, "keyboard_type")
        if "reply_parameters" in config:
            kwargs["reply_parameters"] = self._map_value_to_dict(
                config.pop("reply_parameters"), node, "reply_parameters"
            )
        if config:
            raise _err(node, f"unknown menu setting(s): {', '.join(sorted(config))}")
        return MenuSpec(**kwargs)

    # ── media group ──────────────────────────────────────────────────────
    def _media_group(self, node: Any) -> MediaGroupContentSpec:
        # IDENT LBRACE media_member* RBRACE  (IDENT must be "media_group")
        if _tv(node.children[0]) != "media_group":
            raise _err(node, f"expected 'media_group', got '{_tv(node.children[0])}'")
        items = self._media_members(_rep(node.children[2]))
        return MediaGroupContentSpec(items=items)

    def _media_members(self, members: list[Any]) -> list[Any]:
        out: list[Any] = []
        for member in members:
            child = member.children[0]
            kind = _name(child)
            if kind == "media_item":
                out.append(self._media_item(child))
            elif kind == "media_foreach":
                out.append(self._foreach(child, self._media_block))
            else:  # media_if
                out.append(self._if(child, self._media_block))
        return out

    def _media_block(self, block: Any) -> list[Any]:
        # media_block -> LBRACE media_member* RBRACE
        return self._media_members(_rep(block.children[1]))

    def _media_item(self, node: Any) -> MediaItemNode:
        # IDENT expr media_satellite*
        media_type = _tv(node.children[0])
        if media_type not in _MEDIA_TYPES:
            raise _err(node, f"unknown media type '{media_type}' ({', '.join(sorted(_MEDIA_TYPES))})")
        media = self._expr(node.children[1])
        sats: dict[str, Any] = {}
        for sat in _rep(node.children[2]):  # media_satellite -> IDENT COLON expr
            key = _tv(sat.children[0])
            sats[key] = self._expr(sat.children[2])
        allowed = {"caption", "has_spoiler"}
        extra = set(sats) - allowed
        if extra:
            raise _err(node, f"unexpected media field(s): {', '.join(sorted(extra))}")
        return MediaItemNode(
            media_type=media_type, media=media,
            caption=sats.get("caption"), has_spoiler=sats.get("has_spoiler"),
        )

    # ── value (menu/row/def child) ───────────────────────────────────────
    def _value(self, node: Any) -> Any:
        child = node.children[0]
        kind = _name(child)
        if kind == "expr":
            return self._expr(child)
        if kind == "button_decl":
            return self._button(child)
        if kind == "row":
            return self._row(child)
        if kind == "if_stmt":
            return self._if(child, self._block)
        if kind == "foreach_stmt":
            return self._foreach(child, self._block)
        if kind == "chunk_stmt":
            return self._chunk(child)
        raise _err(child, f"unexpected construct '{kind}'")  # pragma: no cover

    def _block(self, block: Any) -> list[Any]:
        # block -> LBRACE value* RBRACE
        return [self._value(v) for v in _rep(block.children[1])]

    def _row(self, node: Any) -> RowNode:
        # ROW LBRACK value_list? RBRACK
        if len(node.children) == 3:
            return RowNode(items=[])
        return RowNode(items=self._value_list(node.children[2]))

    def _value_list(self, node: Any) -> list[Any]:
        # value_list -> value | value COMMA value_list
        out = [self._value(node.children[0])]
        while len(node.children) == 3:
            node = node.children[2]
            out.append(self._value(node.children[0]))
        return out

    def _button(self, node: Any) -> ButtonSpec:
        # BUTTON IDENT map  |  BUTTON map
        if _is_term(node.children[1]):  # named
            name = _tv(node.children[1])
            config = self._map(node.children[2])
        else:
            name = f"button#{self._btn_counter}"
            self._btn_counter += 1
            config = self._map(node.children[1])
        text = config.pop("text", None)
        if text is None:
            raise _err(node, f"button '{name}' has no text")
        data = self._as_dict(config.pop("data", None), node, "data")
        inline = self._as_dict(config.pop("inline", None), node, "inline")
        common = self._as_dict(config.pop("common", None), node, "common")
        type_name = None
        if "type_name" in config:
            type_name = self._literal_str(config.pop("type_name"), node, f"button '{name}' type_name")
        if config:
            raise _err(node, f"unknown button field(s): {', '.join(sorted(config))}")
        return ButtonSpec(name=name, text=text, data=data or {}, inline=inline, common=common, type_name=type_name)

    def _if(self, node: Any, block_builder: Callable[[Any], list]) -> IfNode:
        # IF expr block (ELSE block)?
        when = self._expr(node.children[1])
        then = block_builder(node.children[2])
        if len(node.children) > 3:  # ... ELSE block
            return IfNode(when=when, then=then, else_=block_builder(node.children[4]))
        return IfNode(when=when, then=then)

    def _foreach(self, node: Any, block_builder: Callable[[Any], list]) -> ForeachNode:
        # FOREACH IDENT IN expr block  |  FOREACH IDENT COMMA IDENT IN expr block
        var = _tv(node.children[1])
        if _name(node.children[2]) == "COMMA":
            index_var = _tv(node.children[3])
            over = self._expr(node.children[5])
            body = block_builder(node.children[6])
        else:
            index_var = None
            over = self._expr(node.children[3])
            body = block_builder(node.children[4])
        return ForeachNode(over=over, body=body, var=var, index_var=index_var)

    def _chunk(self, node: Any) -> ChunkNode:
        # CHUNK expr block
        size = self._expr(node.children[1])
        items = self._block(node.children[2])
        return ChunkNode(size=size, items=items)

    # ── expressions ──────────────────────────────────────────────────────
    def _expr(self, node: Any) -> Any:
        name = _name(node)
        if name == "expr":
            return self._expr(node.children[0])
        if name in ("or_expr", "and_expr", "add_expr", "mul_expr"):
            if len(node.children) == 1:
                return self._expr(node.children[0])
            op = _tv(node.children[1])
            return OpNode(op=op, args=[self._expr(node.children[0]), self._expr(node.children[2])])
        if name == "cmp_expr":
            if len(node.children) == 1:
                return self._expr(node.children[0])
            if len(node.children) == 4:  # left NOT IN right
                return OpNode(op="not in", args=[self._expr(node.children[0]), self._expr(node.children[3])])
            op = _tv(node.children[1])
            return OpNode(op=op, args=[self._expr(node.children[0]), self._expr(node.children[2])])
        if name == "not_expr":
            if len(node.children) == 1:
                return self._expr(node.children[0])
            return OpNode(op="not", args=[self._expr(node.children[1])])
        if name == "unary":
            if len(node.children) == 1:
                return self._expr(node.children[0])
            return self._negate(self._expr(node.children[1]))
        if name == "primary":
            return self._primary(node)
        raise _err(node, f"unexpected expression node '{name}'")  # pragma: no cover

    def _negate(self, value: Any) -> Any:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return -value
        return OpNode(op="-", args=[0, value])

    def _primary(self, node: Any) -> Any:
        head = node.children[0]
        if _is_term(head):
            tname = _name(head)
            if tname == "NUMBER":
                return self._number(_tv(head))
            if tname == "STRING":
                return self._string(head)
            if tname == "TRUE":
                return True
            if tname == "FALSE":
                return False
            if tname == "NULL":
                return None
            if tname == "LPAREN":  # LPAREN expr RPAREN
                return self._expr(node.children[1])
            if tname == "LBRACK":  # list literal
                if len(node.children) == 2:
                    return []
                return self._value_list(node.children[1])
            raise _err(head, f"unexpected token '{tname}'")  # pragma: no cover
        kind = _name(head)
        if kind == "path":
            return PathNode(path=self._path(head))
        if kind == "call":
            return self._call(head)
        if kind == "t_call":
            return self._t(head)
        if kind == "provider_call":
            return self._provider(head)
        if kind == "ref_call":
            return self._ref(head)
        if kind == "slice_call":
            return self._slice(head)
        if kind == "proto_call":
            return self._proto(head)
        if kind == "escape_call":
            return self._escape(head)
        if kind == "node_call":
            return self._node(head)
        if kind == "map":
            return self._map(head)
        raise _err(head, f"unexpected primary '{kind}'")  # pragma: no cover

    def _path(self, node: Any) -> str:
        # path -> IDENT | path DOT IDENT | path DOT NUMBER
        if len(node.children) == 1:
            return _tv(node.children[0])
        return f"{self._path(node.children[0])}.{_tv(node.children[2])}"

    def _call(self, node: Any) -> CallNode:
        # IDENT LPAREN arg_list? RPAREN
        name = _tv(node.children[0])
        args = self._arg_list(node.children[2]) if len(node.children) == 4 else []
        return CallNode(name=name, args=args)

    def _arg_list(self, node: Any) -> list[Any]:
        # arg_list -> expr | expr COMMA arg_list
        out = [self._expr(node.children[0])]
        while len(node.children) == 3:
            node = node.children[2]
            out.append(self._expr(node.children[0]))
        return out

    def _t(self, node: Any) -> TranslateNode:
        # T LPAREN expr RPAREN
        key = self._literal_str(self._expr(node.children[2]), node, "t() key")
        return TranslateNode(key=key)

    def _provider(self, node: Any) -> ProviderNode:
        # PROVIDER LPAREN expr (COMMA pair_list)? RPAREN
        name = self._literal_str(self._expr(node.children[2]), node, "provider() name")
        args: dict[str, Any] = {}
        if len(node.children) == 6:  # ... COMMA pair_list RPAREN
            args = self._pair_list(node.children[4])
        return ProviderNode(name=name, args=args)

    def _ref(self, node: Any) -> RefNode:
        # REF IDENT | REF LPAREN expr RPAREN
        if _is_term(node.children[1]) and _name(node.children[1]) == "IDENT":
            return RefNode(name=_tv(node.children[1]))
        name = self._literal_str(self._expr(node.children[2]), node, "ref() name")
        return RefNode(name=name)

    def _slice(self, node: Any) -> SliceNode:
        # SLICE LPAREN arg_list RPAREN
        args = self._arg_list(node.children[2])
        if not 1 <= len(args) <= 3:
            raise _err(node, "slice() takes 1 to 3 arguments (over, start, stop)")
        over = args[0]
        start = args[1] if len(args) >= 2 else None
        stop = args[2] if len(args) == 3 else None
        return SliceNode(over=over, start=start, stop=stop)

    def _proto(self, node: Any) -> Any:
        # proto_call -> BUTTON LPAREN expr RPAREN
        name = self._literal_str(self._expr(node.children[2]), node, "button() name")
        return UseButtonNode(name=name)

    def _escape(self, node: Any) -> EscapeNode:
        # escape_call -> ESCAPE map | ESCAPE LPAREN RPAREN
        if len(node.children) == 2:  # ESCAPE map
            return EscapeNode(entries=self._map(node.children[1]))
        return EscapeNode(entries={})  # ESCAPE LPAREN RPAREN

    def _node(self, node: Any) -> SpecNode:
        # node_call -> NODE LPAREN expr (COMMA pair_list)? RPAREN
        # Generic escape hatch: build any registered node kind by type name.
        type_name = self._literal_str(self._expr(node.children[2]), node, "node() type")
        fields = self._pair_list(node.children[4]) if len(node.children) == 6 else {}
        if "type" in fields:
            raise _err(node, "node() takes the type as its first argument; drop the 'type' field")
        return node_registry.create({"type": type_name, **fields})

    # ── maps / helpers ───────────────────────────────────────────────────
    def _map(self, node: Any) -> dict[str, Any]:
        # map -> LPAREN pair_list RPAREN
        return self._pair_list(node.children[1])

    def _pair_list(self, node: Any) -> dict[str, Any]:
        # pair_list -> pair | pair COMMA pair_list ; pair -> IDENT EQ expr
        out: dict[str, Any] = {}
        while True:
            pair = node.children[0]
            key = _tv(pair.children[0])
            if key in out:
                raise _err(pair, f"duplicate key '{key}'")
            out[key] = self._expr(pair.children[2])
            if len(node.children) == 3:
                node = node.children[2]
            else:
                break
        return out

    def _string(self, term: Any) -> Any:
        return parse_string(_tv(term), self._parse_expr_text)

    @staticmethod
    def _number(text: str) -> Any:
        return float(text) if "." in text else int(text)

    def _as_dict(self, value: Any, node: Any, field: str) -> Optional[dict]:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise _err(node, f"button '{field}' must be a (k=v) map")
        return value

    def _map_value_to_dict(self, value: Any, node: Any, field: str) -> dict:
        if not isinstance(value, dict):
            raise _err(node, f"'{field}' must be a (k=v) map")
        return value

    def _literal_str(self, value: Any, node: Any, what: str) -> str:
        if not isinstance(value, str):
            raise _err(node, f"{what} must be a string literal (dynamic values are not supported here)")
        return value

    def _literal_int(self, value: Any, node: Any, what: str) -> int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        raise _err(node, f"{what} must be an integer literal")
