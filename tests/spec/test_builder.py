"""Tests for the Python builder and its widgets."""
import pytest

from aiogram_dialog_manager.spec import (
    ButtonSpec,
    CallNode,
    ChunkNode,
    DialogSpec,
    DocumentContentSpec,
    EscapeNode,
    ForeachNode,
    FormatNode,
    IfNode,
    LiteralNode,
    MediaGroupContentSpec,
    MediaItemNode,
    MenuSpec,
    OpNode,
    PathNode,
    PhotoContentSpec,
    ProviderNode,
    RefNode,
    RowNode,
    SliceNode,
    TranslateNode,
    WindowSpec,
    compile_dialog,
)
from aiogram_dialog_manager.spec import builder as b
from tests.spec.conftest import FakeDialog


def node(expr) -> object:
    return expr.__spec_node__()


class TestExpressionHelpers:
    def test_path_and_proxies(self):
        assert node(b.path("data.x")) == PathNode(path="data.x")
        assert node(b.data_.page) == PathNode(path="data.page")
        assert node(b.ctx_.locale) == PathNode(path="ctx.locale")
        assert node(b.item_.id) == PathNode(path="item.id")
        assert node(b.index_) == PathNode(path="index")
        assert node(b.data_.items[0]) == PathNode(path="data.items.0")
        assert node(b.data_.a.b.c) == PathNode(path="data.a.b.c")

    def test_private_attribute_access_raises(self):
        with pytest.raises(AttributeError):
            b.data_._private

    def test_escape_keeps_type_key(self):
        assert node(b.escape({"type": "premium", "count": b.data_.n})) == EscapeNode(
            entries={"type": "premium", "count": PathNode(path="data.n")}
        )

    def test_lit_fn_t_provider_ref(self):
        assert node(b.lit({"type": "raw"})) == LiteralNode(value={"type": "raw"})
        assert node(b.fn("len", b.data_.items)) == CallNode(name="len", args=[PathNode(path="data.items")])
        assert node(b.fn("round", 1.5, ndigits=1)) == CallNode(name="round", args=[1.5], kwargs={"ndigits": 1})
        assert node(b.t("welcome")) == TranslateNode(key="welcome")
        assert node(b.format_(b.t("greet"), name=b.data_.name)) == FormatNode(
            template=TranslateNode(key="greet"), kwargs={"name": PathNode(path="data.name")},
        )
        assert node(b.format_("{0}", b.data_.n)) == FormatNode(template="{0}", args=[PathNode(path="data.n")])
        assert node(b.provider("top", limit=5)) == ProviderNode(name="top", args={"limit": 5})
        assert node(b.ref("back")) == RefNode(name="back")

    @pytest.mark.parametrize("expr,op,args", [
        (lambda: b.data_.x < 1, "<", [PathNode(path="data.x"), 1]),
        (lambda: b.data_.x > 1, ">", [PathNode(path="data.x"), 1]),
        (lambda: b.data_.x <= 1, "<=", [PathNode(path="data.x"), 1]),
        (lambda: b.data_.x >= 1, ">=", [PathNode(path="data.x"), 1]),
        (lambda: b.data_.x == 1, "==", [PathNode(path="data.x"), 1]),
        (lambda: b.data_.x != 1, "!=", [PathNode(path="data.x"), 1]),
        (lambda: b.data_.x + 1, "+", [PathNode(path="data.x"), 1]),
        (lambda: 1 + b.data_.x, "+", [1, PathNode(path="data.x")]),
        (lambda: b.data_.x - 1, "-", [PathNode(path="data.x"), 1]),
        (lambda: 1 - b.data_.x, "-", [1, PathNode(path="data.x")]),
        (lambda: b.data_.x * 2, "*", [PathNode(path="data.x"), 2]),
        (lambda: 2 * b.data_.x, "*", [2, PathNode(path="data.x")]),
        (lambda: b.data_.x / 2, "/", [PathNode(path="data.x"), 2]),
        (lambda: 2 / b.data_.x, "/", [2, PathNode(path="data.x")]),
        (lambda: b.data_.x % 2, "%", [PathNode(path="data.x"), 2]),
        (lambda: 2 % b.data_.x, "%", [2, PathNode(path="data.x")]),
        (lambda: b.data_.a & b.data_.b, "and", [PathNode(path="data.a"), PathNode(path="data.b")]),
        (lambda: b.data_.a | "fallback", "or", [PathNode(path="data.a"), "fallback"]),
        (lambda: ~b.data_.a, "not", [PathNode(path="data.a")]),
    ])
    def test_operator_overloads(self, expr, op, args):
        assert node(expr()) == OpNode(op=op, args=args)

    def test_logic_helpers(self):
        assert node(b.and_(True, b.data_.x)) == OpNode(op="and", args=[True, PathNode(path="data.x")])
        assert node(b.or_(b.data_.x, "d")) == OpNode(op="or", args=[PathNode(path="data.x"), "d"])
        assert node(b.not_(b.data_.x)) == OpNode(op="not", args=[PathNode(path="data.x")])
        assert node(b.in_(1, b.data_.items)) == OpNode(op="in", args=[1, PathNode(path="data.items")])
        assert node(b.not_in(1, b.data_.items)) == OpNode(op="not in", args=[1, PathNode(path="data.items")])

    def test_as_expr(self):
        expr = b.data_.x
        assert b.as_expr(expr) is expr
        assert node(b.as_expr(PathNode(path="data.y"))) == PathNode(path="data.y")
        assert node(b.as_expr(5)) == LiteralNode(value=5)


class TestStructuralHelpers:
    def test_if_without_else(self):
        built = b.if_(b.data_.x, "yes")
        assert isinstance(built, IfNode)
        assert "else_" not in built.model_fields_set

    def test_if_with_else(self):
        built = b.if_(b.data_.x, "yes", "no")
        assert built.else_ == "no"

    def test_foreach_chunk_slice_row(self):
        assert isinstance(b.foreach(b.data_.items, b.item_), ForeachNode)
        assert isinstance(b.chunk(2, "a", "b"), ChunkNode)
        assert isinstance(b.slice_(b.data_.items, 0, 5), SliceNode)
        assert isinstance(b.row("a", "b"), RowNode)

    def test_button(self):
        built = b.button("save", "Save", data={"x": 1}, inline={"url": "https://e.com"}, common={"request_contact": True})
        assert isinstance(built, ButtonSpec)
        assert built.data == {"x": 1}
        assert built.inline == {"url": "https://e.com"}
        assert b.button("simple", "S").data == {}


class TestContentAndModelHelpers:
    def test_text_single_and_fragments(self):
        assert b.text("Hello").text == "Hello"
        fragments = b.text("Hi, ", b.data_.name).text
        assert fragments[0] == "Hi, " and isinstance(fragments[1], PathNode)

    def test_photo_document_media_group(self):
        assert isinstance(b.photo("fid", "cap", has_spoiler=True), PhotoContentSpec)
        assert isinstance(b.document("did", disable_content_type_detection=True), DocumentContentSpec)
        group = b.media_group(b.media_item("photo", "f1"), b.media_item("video", "f2", has_spoiler=True))
        assert isinstance(group, MediaGroupContentSpec)
        assert all(isinstance(item, MediaItemNode) for item in group.items)

    def test_content_send_params(self):
        content = b.text("hi", send_params={"parse_mode": "HTML", "link_preview_options": b.data_.lpo})
        assert content.send_params["parse_mode"] == "HTML"
        assert isinstance(content.send_params["link_preview_options"], PathNode)
        assert b.text("hi").send_params is None
        assert b.photo("f", send_params={"protect_content": True}).send_params == {"protect_content": True}

    def test_menu_window_dialog(self):
        spec = b.dialog(
            "settings",
            windows={"main": b.window(b.text("Hi"), menu=b.menu(b.row(b.button("ok", "OK"))))},
            defs={"back": b.button("back", "Back")},
        )
        assert isinstance(spec, DialogSpec)
        assert isinstance(spec.windows["main"], WindowSpec)
        assert isinstance(spec.windows["main"].menu, MenuSpec)
        assert isinstance(spec.defs["back"], ButtonSpec)

    def test_menu_reply_parameters(self):
        built = b.menu(b.row(b.button("ok", "OK")), keyboard_type="reply", reply_parameters={"selective": True})
        assert built.keyboard_type == "reply"
        assert built.reply_parameters == {"selective": True}

    def test_built_dialog_serializes_and_compiles(self):
        spec = b.dialog("d", windows={"w": b.window(b.text("Hello, ", b.data_.name | "anon"))})
        assert DialogSpec.from_dict(spec.to_dict()) == spec
        compiled = compile_dialog(spec)
        assert compiled.windows.w.message.name == "d:w"


class TestPaginator:
    def make_menu_prototype(self, page_size=2, per_row=2):
        spec = b.dialog("d", windows={"w": b.window(
            b.text("players"),
            menu=b.menu(*b.paginator(
                "pl",
                over=b.data_.players,
                page=b.data_.page,
                item=b.button("player", b.item_.name, data={"pid": b.item_.id}),
                page_size=page_size,
                per_row=per_row,
            )),
        )})
        return compile_dialog(spec).windows.w

    @staticmethod
    def players(count):
        return [{"id": i, "name": f"P{i}"} for i in range(count)]

    async def test_middle_page_has_both_nav_buttons(self):
        window = self.make_menu_prototype()
        rows = await window.menu.get_buttons(FakeDialog({"page": 1, "players": self.players(6)}), None)
        assert [[button.text for button in row] for row in rows] == [["P2", "P3"], ["«", "»"]]
        nav = rows[-1]
        assert nav[0].data == {"page": 0}
        assert nav[1].data == {"page": 2}

    async def test_first_page_has_only_next(self):
        window = self.make_menu_prototype()
        rows = await window.menu.get_buttons(FakeDialog({"page": 0, "players": self.players(3)}), None)
        assert [button.text for button in rows[-1]] == ["»"]

    async def test_last_page_has_only_prev(self):
        window = self.make_menu_prototype()
        rows = await window.menu.get_buttons(FakeDialog({"page": 1, "players": self.players(3)}), None)
        assert [[button.text for button in row] for row in rows] == [["P2"], ["«"]]

    async def test_single_page_has_no_nav_row(self):
        window = self.make_menu_prototype()
        rows = await window.menu.get_buttons(FakeDialog({"page": 0, "players": self.players(2)}), None)
        assert [[button.text for button in row] for row in rows] == [["P0", "P1"]]

    def test_serialized_form_is_unpacked(self):
        window = self.make_menu_prototype()
        # The serialized model contains only core primitives — no widget traces.
        dumped = window.menu.spec.model_dump(by_alias=True)
        types = {row["type"] for row in dumped["rows"]}
        assert types == {"chunk", "row"}

    def test_typed_handles_include_nav_buttons(self):
        window = self.make_menu_prototype()
        assert window.buttons.pl_prev.name == "d:w:pl_prev"
        assert window.buttons.pl_next.name == "d:w:pl_next"
        assert window.buttons.player.name == "d:w:player"


async def test_readme_style_example_renders(make_scope):
    """The builder docstring example, end to end."""
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
    compiled = compile_dialog(spec, translator=lambda msgid, locale: {"save_btn": "Сохранить"}.get(msgid, msgid))
    dialog = FakeDialog({"players": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]})
    content = await compiled.windows.main.message.get_text_content(dialog, None)
    assert content.text == "Hello, anonymous!"
    rows = await compiled.windows.main.menu.get_buttons(dialog, None)
    assert [[button.text for button in row] for row in rows] == [["Сохранить"], ["A"], ["B"]]


class TestUseAndWindowDataHelpers:
    def test_use_button(self):
        node_ = b.use_button("cancel_btn", context={"page": b.data_.page})
        assert node_.type == "use_button"
        assert node_.name == "cancel_btn"
        assert node_.context["page"].path == "data.page"

    def test_use_button_without_context(self):
        assert b.use_button("cancel_btn").context is None

    def test_use_menu_in_window(self):
        window = b.window(b.text("hi"), menu=b.use_menu("shared_menu", context={"resize": True}))
        assert window.menu.type == "use_menu"
        assert window.menu.context == {"resize": True}

    def test_use_message_in_window(self):
        window = b.window(b.use_message("error_msg"))
        assert window.content.type == "use_message"
        assert window.content.name == "error_msg"

    def test_window_data_and_dialog_window_name_key(self):
        spec = b.dialog(
            "wizard",
            window_name_key="state",
            windows={"main": b.window(b.text("hi"), data={"page": b.data_.page})},
        )
        assert spec.window_name_key == "state"
        assert spec.windows["main"].data["page"].path == "data.page"
        dumped = spec.to_dict()
        assert dumped["window_name_key"] == "state"
        assert dumped["windows"]["main"]["data"]["page"] == {"type": "path", "path": "data.page"}
