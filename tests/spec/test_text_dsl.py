"""Tests for the textual dialog DSL (parse + transform to the spec model)."""
import pytest

from aiogram_dialog_manager.spec import builder as b
from aiogram_dialog_manager.spec import compile_dialog
from aiogram_dialog_manager.spec.model import DialogSpec
from aiogram_dialog_manager.spec.text import DSLError, DSLSyntaxError, parse_dialog_text


def p(src: str) -> DialogSpec:
    return parse_dialog_text(src)


def win(body: str, *, head: str = "") -> DialogSpec:
    """A single-window dialog wrapping ``body`` (window ``w`` content/menu)."""
    return p(f"dialog d {head} {{ window w {{ {body} }} }}")


def first_content(spec: DialogSpec):
    return spec.windows["w"].content


# ── dialog / top level ───────────────────────────────────────────────────────
def test_minimal_dialog():
    spec = win('text: "hi"')
    assert spec.name == "d"
    assert spec.version == 1
    assert list(spec.windows) == ["w"]


def test_dialog_settings():
    spec = p('dialog d (window_name_key="state", version=1) { window w { text: "hi" } }')
    assert spec.window_name_key == "state"
    assert spec.version == 1


def test_dialog_data_and_config():
    spec = p('dialog d (data=(step=0, uid=ctx.uid), config=(allow_reply_lookup=true)) '
             '{ window w { text: "hi" } }')
    assert spec.data["step"] == 0
    assert spec.config["allow_reply_lookup"] is True


def test_dialog_requires_name():
    with pytest.raises(DSLSyntaxError, match="dialog must have a name"):
        p('dialog { window w { text: "x" } }')


def test_dialog_requires_window():
    with pytest.raises(DSLSyntaxError, match="at least one window"):
        p("dialog d { defs { a: button a (text=\"x\") } }")


def test_unknown_dialog_setting():
    with pytest.raises(DSLSyntaxError, match="unknown dialog setting"):
        p('dialog d (bogus="x") { window w { text: "hi" } }')


def test_version_must_be_int():
    with pytest.raises(DSLSyntaxError, match="version must be an integer"):
        p('dialog d (version="x") { window w { text: "hi" } }')


def test_window_name_key_must_be_string():
    with pytest.raises(DSLSyntaxError, match="window_name_key must be a string"):
        p("dialog d (window_name_key=data.x) { window w { text: \"hi\" } }")


def test_duplicate_window():
    with pytest.raises(DSLSyntaxError, match="duplicate window"):
        p('dialog d { window w { text: "a" } window w { text: "b" } }')


def test_anonymous_window_gets_positional_name():
    spec = p('dialog d { window { text: "a" } window { text: "b" } }')
    assert set(spec.windows) == {"window#0", "window#1"}


# ── content ──────────────────────────────────────────────────────────────────
def test_text_content():
    spec = win('text: "hello"')
    assert first_content(spec).model_dump() == b.text("hello").model_dump()


def test_photo_content_with_satellites():
    spec = win('photo: data.cover  caption: "c"  has_spoiler: true  show_caption_above_media: false')
    got = first_content(spec).model_dump()
    exp = b.photo(b.data_.cover, "c", has_spoiler=True, show_caption_above_media=False).model_dump()
    assert got == exp


def test_document_content():
    spec = win('document: data.file  caption: "c"  disable_content_type_detection: true')
    got = first_content(spec).model_dump()
    exp = b.document(b.data_.file, "c", disable_content_type_detection=True).model_dump()
    assert got == exp


def test_no_content_is_error():
    with pytest.raises(DSLSyntaxError, match="has no content"):
        p("dialog d { window w { menu { row [ button a (text=\"x\") ] } } }")


def test_two_primary_content_fields():
    with pytest.raises(DSLSyntaxError, match="more than one primary"):
        win('text: "a"  photo: data.x')


def test_unexpected_text_field():
    with pytest.raises(DSLSyntaxError, match="unexpected field.*text"):
        win('text: "a"  caption: "c"')


def test_unexpected_photo_field():
    with pytest.raises(DSLSyntaxError, match="unexpected field.*photo"):
        win('photo: data.x  disable_content_type_detection: true')


def test_unexpected_document_field():
    with pytest.raises(DSLSyntaxError, match="unexpected field.*document"):
        win('document: data.x  has_spoiler: true')


def test_missing_primary_field():
    with pytest.raises(DSLSyntaxError, match="missing a primary content field"):
        win('caption: "c"')


def test_duplicate_field():
    with pytest.raises(DSLSyntaxError, match="duplicate field"):
        win('text: "a"  text: "b"')


# ── message (explicit + refs) ────────────────────────────────────────────────
def test_explicit_message_block():
    spec = win('message { text: "hi" }')
    assert first_content(spec).model_dump() == b.text("hi").model_dump()


def test_message_ref():
    spec = win('message("my_proto")')
    assert first_content(spec).type == "use_message"
    assert first_content(spec).name == "my_proto"


def test_message_mixed_with_sugar():
    with pytest.raises(DSLSyntaxError, match="mixes an explicit 'message'"):
        win('text: "a"  message { text: "b" }')


def test_two_messages():
    with pytest.raises(DSLSyntaxError, match="more than one message"):
        win('message { text: "a" }  message { text: "b" }')


def test_message_send_params():
    spec = win('message (send_params=(parse_mode="HTML", disable_notification=true)) { text: "a" }')
    content = first_content(spec)
    assert content.type == "text"
    assert content.send_params == {"parse_mode": "HTML", "disable_notification": True}


def test_window_sugar_send_params():
    spec = win('text: "a"', head="")
    assert first_content(spec).send_params is None
    spec = p('dialog d { window w (send_params=(parse_mode="MarkdownV2")) { text: "a" } }')
    assert first_content(spec).send_params == {"parse_mode": "MarkdownV2"}


def test_window_send_params_with_explicit_message_rejected():
    with pytest.raises(DSLSyntaxError, match="put send_params on the message"):
        p('dialog d { window w (send_params=(parse_mode="HTML")) { message { text: "a" } } }')


def test_unknown_message_setting():
    with pytest.raises(DSLSyntaxError, match="unknown message setting"):
        win('message (bogus="x") { text: "a" }')


def test_message_no_content():
    with pytest.raises(DSLSyntaxError, match="message has no content"):
        p('dialog d { window w { message { } menu { row [ button a (text="x") ] } } }')


# ── menu ─────────────────────────────────────────────────────────────────────
def test_menu_with_button():
    spec = win('text: "h"  menu { row [ button save (text="Save") ] }')
    menu = spec.windows["w"].menu
    assert menu.keyboard_type == "inline"
    assert menu.rows[0].items[0].name == "save"


def test_menu_keyboard_type_and_reply_params():
    spec = win('text: "h"  menu (keyboard_type="reply", reply_parameters=(resize_keyboard=true)) { row [] }')
    menu = spec.windows["w"].menu
    assert menu.keyboard_type == "reply"
    assert menu.reply_parameters == {"resize_keyboard": True}


def test_menu_ref():
    spec = win('text: "h"  menu("shared")')
    assert spec.windows["w"].menu.type == "use_menu"
    assert spec.windows["w"].menu.name == "shared"


def test_two_menus_error():
    with pytest.raises(DSLSyntaxError, match="more than one menu"):
        win('text: "h"  menu { row [] }  menu { row [] }')


def test_unknown_menu_setting():
    with pytest.raises(DSLSyntaxError, match="unknown menu setting"):
        win('text: "h"  menu (bogus="x") { row [] }')


def test_empty_row():
    spec = win('text: "h"  menu { row [] }')
    assert spec.windows["w"].menu.rows[0].items == []


# ── window config (data) ─────────────────────────────────────────────────────
def test_window_data():
    spec = win('text: "h"', head="")  # placeholder
    spec = p('dialog d { window w (data=(attempts=0)) { text: "h" } }')
    assert spec.windows["w"].data == {"attempts": 0}


def test_window_message_name_override():
    assert win('text: "h"').windows["w"].message_name is None
    spec = p('dialog d { window w (message_name="legacy_topic") { text: "h" } }')
    assert spec.windows["w"].message_name == "legacy_topic"


def test_window_message_name_must_be_string():
    with pytest.raises(DSLSyntaxError, match="message_name must be a string literal"):
        p('dialog d { window w (message_name=data.x) { text: "h" } }')


def test_unknown_window_setting():
    with pytest.raises(DSLSyntaxError, match="unknown window setting"):
        p('dialog d { window w (bogus=1) { text: "h" } }')


# ── buttons ──────────────────────────────────────────────────────────────────
def test_button_full():
    spec = win('text: "h"  menu { row [ button pay (text=t("buy"), data=(order=data.id), inline=(url="u")) ] } ')
    btn = spec.windows["w"].menu.rows[0].items[0]
    exp = b.button("pay", b.t("buy"), data={"order": b.data_.id}, inline={"url": "u"}).model_dump()
    assert btn.model_dump() == exp


def test_button_common_channel():
    spec = win('text: "h"  menu { row [ button share (text="p", common=(request_contact=true)) ] }')
    btn = spec.windows["w"].menu.rows[0].items[0]
    assert btn.common == {"request_contact": True}


def test_button_type_name_override():
    spec = win('text: "h"  menu { row [ button fresh (text="x", type_name="cancel") ] }')
    btn = spec.windows["w"].menu.rows[0].items[0]
    assert btn.type_name == "cancel"


def test_button_type_name_must_be_string():
    with pytest.raises(DSLSyntaxError, match="type_name must be a string literal"):
        win('text: "h"  menu { row [ button a (text="x", type_name=data.n) ] }')


def test_button_missing_text():
    with pytest.raises(DSLSyntaxError, match="has no text"):
        win('text: "h"  menu { row [ button a (data=(x=1)) ] }')


def test_button_unknown_field():
    with pytest.raises(DSLSyntaxError, match="unknown button field"):
        win('text: "h"  menu { row [ button a (text="x", bogus=1) ] }')


def test_button_data_must_be_map():
    with pytest.raises(DSLSyntaxError, match="button 'data' must be a"):
        win('text: "h"  menu { row [ button a (text="x", data=1) ] }')


def test_anonymous_buttons_get_positional_names():
    spec = win('text: "h"  menu { row [ button (text="a"), button (text="b") ] }')
    names = [item.name for item in spec.windows["w"].menu.rows[0].items]
    assert names == ["button#0", "button#1"]


def test_button_ref_static():
    spec = win('text: "h"  menu { row [ button("cancel_btn") ] }')
    item = spec.windows["w"].menu.rows[0].items[0]
    assert item.type == "use_button"
    assert item.name == "cancel_btn"


def test_button_ref_dynamic_unsupported():
    with pytest.raises(DSLSyntaxError, match="button\\(\\) name must be a string literal"):
        win('text: "h"  menu { row [ button(data.which) ] }')


# ── defs / ref ───────────────────────────────────────────────────────────────
def test_defs_and_ref():
    spec = p(
        'dialog d { defs { back: button back (text="B") } '
        'window w { text: "h" menu { row [ ref back ] } } }'
    )
    assert spec.defs["back"].name == "back"
    assert spec.windows["w"].menu.rows[0].items[0].type == "ref"


def test_ref_dynamic_string():
    spec = p('dialog d { defs { back: button back (text="B") } window w { text: "h" menu { ref("back") } } }')
    assert spec.windows["w"].menu.rows[0].name == "back"


def test_ref_dynamic_unsupported():
    with pytest.raises(DSLSyntaxError, match="ref\\(\\) name must be a string literal"):
        p('dialog d { defs { back: button back (text="B") } window w { text: "h" menu { ref(data.x) } } }')


def test_duplicate_def():
    with pytest.raises(DSLSyntaxError, match="duplicate def"):
        p('dialog d { defs { a: button a (text="x") a: button a2 (text="y") } window w { text: "h" } }')


def test_def_list_of_rows():
    spec = p(
        'dialog d { defs { nav: [ row [ button a (text="x") ], row [ button z (text="y") ] ] } '
        'window w { text: "h" } }'
    )
    assert isinstance(spec.defs["nav"], list)
    assert len(spec.defs["nav"]) == 2


# ── structural ───────────────────────────────────────────────────────────────
def test_if_else():
    spec = win(
        'text: "h"  menu { if data.admin { row [ button a (text="x") ] } '
        'else { row [ button b (text="y") ] } }'
    )
    node = spec.windows["w"].menu.rows[0]
    assert node.type == "if"
    assert node.else_ is not None


def test_if_no_else():
    spec = win('text: "h"  menu { if data.admin { row [ button a (text="x") ] } }')
    assert spec.windows["w"].menu.rows[0].else_ is None


def test_foreach_simple():
    spec = win('text: "h"  menu { foreach x in data.p { row [ button b (text=x.name) ] } }')
    node = spec.windows["w"].menu.rows[0]
    assert node.type == "foreach"
    assert node.var == "x"
    assert node.index_var is None


def test_foreach_with_index():
    spec = win('text: "h"  menu { foreach x, i in data.p { row [ button b (text=x.name) ] } }')
    node = spec.windows["w"].menu.rows[0]
    assert node.var == "x"
    assert node.index_var == "i"


def test_chunk():
    spec = win('text: "h"  menu { chunk 2 { button a (text="x") button z (text="y") } }')
    node = spec.windows["w"].menu.rows[0]
    assert node.type == "chunk"
    assert node.size == 2
    assert len(node.items) == 2


def test_structural_inside_row():
    spec = win('text: "h"  menu { row [ if data.p > 0 { button prev (text="<") }, button next (text=">") ] }')
    items = spec.windows["w"].menu.rows[0].items
    assert items[0].type == "if"


# ── expressions ──────────────────────────────────────────────────────────────
def _expr_of(src_value: str):
    spec = win(f'text: "h"  menu {{ row [ button a (text="x", data=(v={src_value})) ] }}')
    return spec.windows["w"].menu.rows[0].items[0].data["v"]


def test_arithmetic_precedence():
    node = _expr_of("1 + 2 * 3")
    # + at the top, * nested on the right
    assert node.op == "+"
    assert node.args[1].op == "*"


def test_comparison_and_logic():
    node = _expr_of("data.a > 0 and data.b <= 10 or not data.c")
    assert node.op == "or"


def test_all_operators():
    for op in ["<", ">", "<=", ">=", "==", "!=", "+", "-", "*", "/", "%"]:
        node = _expr_of(f"data.a {op} data.b")
        assert node.op == op


def test_in_and_not_in():
    assert _expr_of("data.x in data.list").op == "in"
    assert _expr_of("data.x not in data.list").op == "not in"


def test_unary_minus_literal():
    assert _expr_of("-5") == -5


def test_unary_minus_expr():
    node = _expr_of("-data.x")
    assert node.op == "-"
    assert node.args[0] == 0


def test_grouping():
    node = _expr_of("(1 + 2) * 3")
    assert node.op == "*"
    assert node.args[0].op == "+"


def test_literals():
    assert _expr_of("true") is True
    assert _expr_of("false") is False
    assert _expr_of("null") is None
    assert _expr_of("3.5") == 3.5
    assert _expr_of('"txt"') == "txt"


def test_path_and_index():
    node = _expr_of("data.players.0.name")
    assert node.path == "data.players.0.name"


def test_call():
    node = _expr_of('join(data.tags, ", ")')
    assert node.name == "join"
    assert len(node.args) == 2


def test_call_no_args():
    node = _expr_of("now()")
    assert node.name == "now"
    assert node.args == []


def test_provider():
    node = _expr_of('provider("top", limit=10)')
    assert node.name == "top"
    assert node.args == {"limit": 10}


def test_provider_no_args():
    node = _expr_of('provider("top")')
    assert node.args == {}


def test_slice():
    node = _expr_of("slice(data.p, 0, 5)")
    assert node.type == "slice"
    assert node.stop == 5


def test_slice_one_arg():
    node = _expr_of("slice(data.p)")
    assert node.start is None and node.stop is None


def test_slice_too_many_args():
    with pytest.raises(DSLSyntaxError, match="slice\\(\\) takes 1 to 3"):
        _expr_of("slice(data.p, 0, 5, 9)")


def test_map_literal_value():
    node = _expr_of("(a=1, b=2)")
    assert node == {"a": 1, "b": 2}


def test_list_literal_value():
    node = _expr_of("[1, 2, 3]")
    assert node == [1, 2, 3]


def test_empty_list_literal():
    assert _expr_of("[]") == []


def test_t_static():
    spec = win('text: t("welcome")')
    assert first_content(spec).text.type == "t"
    assert first_content(spec).text.key == "welcome"


def test_t_dynamic_unsupported():
    with pytest.raises(DSLSyntaxError, match="t\\(\\) key must be a string literal"):
        win("text: t(data.key)")


def test_duplicate_map_key():
    with pytest.raises(DSLSyntaxError, match="duplicate key"):
        _expr_of("(a=1, a=2)")


# ── strings / interpolation ──────────────────────────────────────────────────
def test_plain_string():
    assert first_content(win('text: "hello"')).text == "hello"


def test_interpolation():
    frag = first_content(win('text: "Hi {data.name}!"')).text
    assert frag[0] == "Hi "
    assert frag[1].path == "data.name"
    assert frag[2] == "!"


def test_interpolation_only_expr():
    frag = first_content(win('text: "{data.name}"')).text
    assert frag[0].path == "data.name"


def test_brace_escape():
    assert first_content(win('text: "a {{ b }} c"')).text == "a { b } c"


def test_string_escapes():
    assert first_content(win('text: "line\\ntab\\tq\\"end"')).text == 'line\ntab\tq"end'


def test_single_quotes():
    assert first_content(win("text: 'hello'")).text == "hello"


def test_nested_quote_in_hole():
    frag = first_content(win('text: "{t(\'k\')} x"')).text
    assert frag[0].type == "t"


def test_empty_string():
    assert first_content(win('text: ""')).text == ""


def test_unterminated_interpolation():
    with pytest.raises(DSLSyntaxError, match="unterminated"):
        win('text: "a {data.x"')


def test_empty_interpolation():
    with pytest.raises(DSLSyntaxError, match="empty '\\{\\}'"):
        win('text: "a {} b"')


def test_unmatched_close_brace():
    with pytest.raises(DSLSyntaxError, match="unmatched"):
        win('text: "a } b"')


def test_hole_with_quoted_arg():
    # the quote-skip path in the hole scanner: a quoted arg with a comma inside
    frag = first_content(win('text: "{join(data.tags, \', \')}"')).text
    assert frag[0].name == "join"


# ── media group ──────────────────────────────────────────────────────────────
def test_media_group():
    spec = win('media_group { photo data.a caption: "t" video data.b }')
    content = first_content(spec)
    assert content.type == "media_group"
    assert content.items[0].media_type == "photo"
    assert content.items[1].media_type == "video"


def test_media_group_foreach():
    spec = win('media_group { foreach ph in data.photos { photo ph.file_id caption: "{ph.title}" } }')
    assert first_content(spec).items[0].type == "foreach"


def test_media_group_if():
    spec = win('media_group { if data.show { photo data.a } else { photo data.b } }')
    assert first_content(spec).items[0].type == "if"


def test_media_group_with_index():
    spec = win('media_group { foreach ph, i in data.photos { photo ph.file_id } }')
    assert first_content(spec).items[0].index_var == "i"


def test_media_item_has_spoiler():
    spec = win('media_group { photo data.a has_spoiler: true }')
    assert first_content(spec).items[0].has_spoiler is True


def test_unknown_media_type():
    with pytest.raises(DSLSyntaxError, match="unknown media type"):
        win('media_group { sticker data.a }')


def test_unexpected_media_field():
    with pytest.raises(DSLSyntaxError, match="unexpected media field"):
        win('media_group { photo data.a bogus: 1 }')


def test_not_media_group_keyword():
    with pytest.raises(DSLSyntaxError, match="expected 'media_group'"):
        win('gallery { photo data.a }')


def test_media_group_combined_with_field():
    with pytest.raises(DSLSyntaxError, match="cannot be combined"):
        win('caption: "c"  media_group { photo data.a }')


def test_two_media_groups():
    with pytest.raises(DSLSyntaxError, match="more than one media group"):
        p('dialog d { window w { message { media_group { photo data.a } media_group { photo data.b } } } }')


# ── comments / whitespace ────────────────────────────────────────────────────
def test_comments():
    spec = p("""
    dialog d { // line comment
      window w {
        /* block
           comment */
        text: "hi"
      }
    }
    """)
    assert first_content(spec).text == "hi"


# ── error handling / plumbing ────────────────────────────────────────────────
def test_syntax_error_is_dsl_error():
    assert issubclass(DSLSyntaxError, DSLError)


def test_bad_syntax_raises():
    with pytest.raises(DSLSyntaxError, match="parse failed"):
        p("dialog d { window w { text: } }")


def test_tokenization_error():
    with pytest.raises(DSLSyntaxError):
        p("dialog d { window w { text: `bad` } }")


def test_error_with_position():
    err = DSLSyntaxError("boom", line=3, col=5)
    assert err.line == 3 and err.col == 5
    assert "line 3, col 5" in str(err)


def test_error_line_only():
    assert "line 3" in str(DSLSyntaxError("boom", line=3))


def test_message_duplicate_field():
    with pytest.raises(DSLSyntaxError, match="duplicate field"):
        win('message { text: "a"  text: "b" }')


def test_window_data_not_a_map():
    with pytest.raises(DSLSyntaxError, match="'data' must be a"):
        p("dialog d { window w (data=5) { text: \"h\" } }")


def test_hole_balanced_inner_braces():
    # exercises brace-depth tracking inside a hole; the inner braces are not a
    # valid expression, so it surfaces as an invalid-expression error
    with pytest.raises(DSLSyntaxError, match="invalid expression"):
        win('text: "{ {a} }"')


def test_hole_comment_only_is_empty():
    with pytest.raises(DSLSyntaxError, match="empty expression"):
        win('text: "{ /* c */ }"')


def test_hole_invalid_expression():
    with pytest.raises(DSLSyntaxError, match="invalid expression"):
        win('text: "{1 +}"')


def test_foreach_index_var_runtime():
    import asyncio

    from aiogram_dialog_manager.spec.nodes import ForeachNode, PathNode
    from aiogram_dialog_manager.spec.scope import EvalScope, SpecRuntime

    node = ForeachNode(over=PathNode(path="data.xs"), body=PathNode(path="i"), var="x", index_var="i")

    class _Dlg:
        data = {"xs": ["a", "b", "c"]}

    scope = EvalScope(runtime=SpecRuntime(dialog_name="d"), dialog=_Dlg(), context={})
    result = asyncio.new_event_loop().run_until_complete(node.evaluate(scope))
    assert result.items == [0, 1, 2]


def _eval_expr(node, data=None):
    import asyncio

    from aiogram_dialog_manager.spec.scope import EvalScope, SpecRuntime

    class _Dlg:
        pass

    dlg = _Dlg()
    dlg.data = data or {}
    scope = EvalScope(runtime=SpecRuntime(dialog_name="d"), dialog=dlg, context={})
    return asyncio.new_event_loop().run_until_complete(node.evaluate(scope))


def test_escape_keeps_type_key_and_evaluates_values():
    from aiogram_dialog_manager.spec.nodes import EscapeNode

    node = win('text: escape(type="premium", count=data.n)').windows["w"].content.text
    assert isinstance(node, EscapeNode)
    assert _eval_expr(node, {"n": 3}) == {"type": "premium", "count": 3}


def test_escape_empty():
    from aiogram_dialog_manager.spec.nodes import EscapeNode

    node = win("text: escape()").windows["w"].content.text
    assert isinstance(node, EscapeNode)
    assert _eval_expr(node) == {}


def test_node_generic_constructor():
    from aiogram_dialog_manager.spec.nodes import OpNode

    node = win('text: node("op", op="+", args=[1, data.n])').windows["w"].content.text
    assert isinstance(node, OpNode)
    assert _eval_expr(node, {"n": 4}) == 5


def test_node_without_fields():
    from aiogram_dialog_manager.spec.nodes import LiteralNode

    node = win('text: node("literal")').windows["w"].content.text
    assert isinstance(node, LiteralNode)
    assert _eval_expr(node) is None


def test_node_rejects_type_field():
    with pytest.raises(DSLSyntaxError, match=r"node\(\) takes the type"):
        win('text: node("op", type="x", op="+", args=[1, 2])')


def test_format_node_via_generic_constructor():
    from aiogram_dialog_manager.spec.nodes import FormatNode

    # A format template carries literal braces — escape them (``{{`` / ``}}``) so
    # the DSL string interpolator leaves the ``{a}`` placeholders for str.format.
    node = win('text: node("format", template="{{a}}/{{b}}", kwargs=(a=data.n, b=2))').windows["w"].content.text
    assert isinstance(node, FormatNode)
    assert _eval_expr(node, {"n": 1}) == "1/2"


# ── full round-trip + compile ────────────────────────────────────────────────
FULL = """
dialog create_game (window_name_key="state") {
  defs {
    back: button back (text=t("btn_back"))
  }
  window title_prompt (data=(attempts=0)) {
    text: "Hello, {data.name}!"
    menu (keyboard_type="inline") {
      foreach player, i in data.players {
        row [ button pick (text="{player.name} #{i}", data=(pid=player.0)) ]
      }
      if data.page > 0 {
        row [ button prev (text="<", data=(p=data.page - 1)) ]
      }
      ref back
    }
  }
}
"""


def test_full_round_trip():
    spec = p(FULL)
    d = spec.to_dict()
    DialogSpec.model_validate(d)  # round-trips through the model


def test_full_compiles():
    compiled = compile_dialog(p(FULL))
    assert compiled.windows.title_prompt.buttons.pick.name == "create_game:title_prompt:pick"


def test_dsl_matches_builder():
    dsl = p('dialog d { window w { text: "Hi"  menu { row [ button s (text="Save", data=(id=data.id)) ] } } }')
    built = b.dialog(
        "d",
        windows={"w": b.window(b.text("Hi"), menu=b.menu(b.row(b.button("s", "Save", data={"id": b.data_.id}))))},
    )
    assert dsl.to_dict() == built.to_dict()


def test_foreach_alias_runtime():
    """The core foreach binding: aliases resolve, nested reaches the outer."""
    import asyncio

    from aiogram_dialog_manager.spec.nodes import ForeachNode, PathNode
    from aiogram_dialog_manager.spec.scope import EvalScope, SpecRuntime

    # outer binds `row`; inner iterates the *outer* alias (proving it is visible
    # inside the nested loop) and its body yields each cell.
    inner = ForeachNode(over=PathNode(path="row"), body=PathNode(path="cell"), var="cell")
    outer = ForeachNode(over=PathNode(path="data.rows"), body=inner, var="row")
    runtime = SpecRuntime(dialog_name="d")

    class _Dlg:
        data = {"rows": [["A", "B"]]}

    scope = EvalScope(runtime=runtime, dialog=_Dlg(), context={})
    result = asyncio.new_event_loop().run_until_complete(outer.evaluate(scope))
    assert result.items == ["A", "B"]
