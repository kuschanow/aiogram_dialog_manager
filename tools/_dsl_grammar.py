"""Lexer config and grammar for the textual dialog DSL.

Both are data consumed by ``langforge`` (a local, editable dependency — not a
runtime requirement of the package: importing this module is only needed to
*parse* text specs). The grammar is Earley (accepts the layered, left-recursive
expression grammar without conflict tuning); the lexer is first-match.

The tree shapes produced by langforge EBNF operators are relied upon by
``transform.py``:

- ``x*``   -> right-recursive ``_rep_N`` chain: ``[item, _rep_N]`` or ``[]``
- ``x?``   -> ``_opt_N`` with zero or one child
- ``(...)``-> ``_grp_N`` wrapping the group's children
"""
from __future__ import annotations

#: Reserved words. Lexed as ``KW`` (value carries which word) so they never
#: collide with ``IDENT`` — this is what lets a bare identifier be a reference
#: while keeping ``dialog``/``menu``/... unambiguous (grammar decision D12).
KEYWORDS = [
    "dialog", "window", "menu", "message", "button", "row", "defs",
    "foreach", "in", "if", "else", "chunk", "slice", "ref",
    "t", "provider",
    "and", "or", "not",
    "true", "false", "null",
]

LEXER_CONFIG = {
    "pattern_defs": {
        "ALPHA": "[A-Za-z_]",
        "DIGIT": "[0-9]",
    },
    "states": {
        "root": {
            "on_eof": {"emit": ["EOF"]},
            "rules": [
                # whitespace and comments (D16: // line, /* */ block)
                {"pattern": r"[ \t\r\n]+", "skip": True},
                {"pattern": r"//[^\n]*", "skip": True},
                {"pattern": r"/\*[\s\S]*?\*/", "skip": True},
                # strings — both quote styles (D6/D11.4), captured raw incl. quotes
                {"pattern": r'"(?:[^"\\]|\\.)*"', "emit": "STRING"},
                {"pattern": r"'(?:[^'\\]|\\.)*'", "emit": "STRING"},
                # numbers (D16)
                {"pattern": r"%{DIGIT}+(?:\.%{DIGIT}+)?", "emit": "NUMBER"},
                # keywords before IDENT (first-match)
                {"keywords": KEYWORDS, "emit": "KW"},
                {"pattern": r"%{ALPHA}(?:%{ALPHA}|%{DIGIT})*", "emit": "IDENT"},
                # multi-char operators before single-char (first-match)
                {"pattern": r"<=|>=|==|!=", "emit": "SYM"},
                {"pattern": r"[{}()\[\].,:;=<>+\-*/%]", "emit": "SYM"},
            ],
        }
    },
}


def _kw(name: str) -> str:
    return f'terminal {name.upper()} = KW "{name}"'


def _sym(name: str, value: str) -> str:
    return f'terminal {name} = SYM "{value}"'


_TERMINALS = "\n".join([
    *[_kw(k) for k in KEYWORDS],
    "terminal IDENT = IDENT",
    "terminal NUMBER = NUMBER",
    "terminal STRING = STRING",
    _sym("LBRACE", "{"), _sym("RBRACE", "}"),
    _sym("LPAREN", "("), _sym("RPAREN", ")"),
    _sym("LBRACK", "["), _sym("RBRACK", "]"),
    _sym("COMMA", ","), _sym("COLON", ":"), _sym("SEMI", ";"),
    _sym("EQ", "="), _sym("DOT", "."),
    _sym("LT", "<"), _sym("GT", ">"), _sym("LE", "<="), _sym("GE", ">="),
    _sym("EQEQ", "=="), _sym("NE", "!="),
    _sym("PLUS", "+"), _sym("MINUS", "-"),
    _sym("STAR", "*"), _sym("SLASH", "/"), _sym("PERCENT", "%"),
    "terminal EOF = EOF",
])


# The grammar. Kept deliberately explicit (no operator-choice groups) so the
# transform sees operator tokens as direct children. Lists are right-recursive
# for uniform flattening; block members use ``*`` (flattened via ``_rep``).
GRAMMAR = _TERMINALS + r"""

start file
file -> dialog EOF

# ---- dialog ----
dialog -> DIALOG IDENT? map? LBRACE dialog_member* RBRACE
dialog_member -> defs_block
dialog_member -> window


# inline (k=v) map — D5/D18 config, and map-literal expression
map -> LPAREN pair_list RPAREN
pair_list -> pair
pair_list -> pair COMMA pair_list
pair -> IDENT EQ expr

# ---- defs ----
defs_block -> DEFS LBRACE def_entry* RBRACE
def_entry -> IDENT COLON value

# ---- window / message (declarations sharing the uniform shape) ----
window -> WINDOW IDENT? map? LBRACE window_member* RBRACE
window_member -> field
window_member -> media_group
window_member -> menu_decl
window_member -> menu_ref
window_member -> message_decl
window_member -> message_ref
message_decl -> MESSAGE IDENT? map? LBRACE content_member* RBRACE
message_ref -> MESSAGE LPAREN expr RPAREN
content_member -> field
content_member -> media_group

field -> IDENT COLON expr

# ---- menu ----
menu_decl -> MENU IDENT? map? LBRACE value* RBRACE
menu_ref -> MENU LPAREN expr RPAREN

# ---- row ----
row -> ROW LBRACK RBRACK
row -> ROW LBRACK value_list RBRACK
value_list -> value
value_list -> value COMMA value_list

# ---- structural (usable both at menu level and in rows, D16.4) ----
if_stmt -> IF expr block
if_stmt -> IF expr block ELSE block
foreach_stmt -> FOREACH IDENT IN expr block
foreach_stmt -> FOREACH IDENT COMMA IDENT IN expr block
chunk_stmt -> CHUNK expr block
block -> LBRACE value* RBRACE

# ---- button declaration (leaf: name? + config map, D18) ----
button_decl -> BUTTON IDENT map
button_decl -> BUTTON map

# ---- media group (media_group IDENT enforced in transform; not a keyword) ----
# Its own member grammar (media_item never enters the generic `value`, which
# would make `photo x` ambiguous with two bare expressions).
media_group -> IDENT LBRACE media_member* RBRACE
media_member -> media_item
media_member -> media_foreach
media_member -> media_if
media_foreach -> FOREACH IDENT IN expr media_block
media_foreach -> FOREACH IDENT COMMA IDENT IN expr media_block
media_if -> IF expr media_block
media_if -> IF expr media_block ELSE media_block
media_block -> LBRACE media_member* RBRACE
media_item -> IDENT expr media_satellite*
media_satellite -> IDENT COLON expr

# ---- value: anything that can be a child of a menu/row/def ----
value -> expr
value -> button_decl
value -> row
value -> if_stmt
value -> foreach_stmt
value -> chunk_stmt

# ---- expressions (precedence via layering) ----
expr -> or_expr
or_expr -> or_expr OR and_expr
or_expr -> and_expr
and_expr -> and_expr AND not_expr
and_expr -> not_expr
not_expr -> NOT not_expr
not_expr -> cmp_expr
cmp_expr -> cmp_expr LT add_expr
cmp_expr -> cmp_expr GT add_expr
cmp_expr -> cmp_expr LE add_expr
cmp_expr -> cmp_expr GE add_expr
cmp_expr -> cmp_expr EQEQ add_expr
cmp_expr -> cmp_expr NE add_expr
cmp_expr -> cmp_expr IN add_expr
cmp_expr -> cmp_expr NOT IN add_expr
cmp_expr -> add_expr
add_expr -> add_expr PLUS mul_expr
add_expr -> add_expr MINUS mul_expr
add_expr -> mul_expr
mul_expr -> mul_expr STAR unary
mul_expr -> mul_expr SLASH unary
mul_expr -> mul_expr PERCENT unary
mul_expr -> unary
unary -> MINUS unary
unary -> primary

primary -> NUMBER
primary -> STRING
primary -> TRUE
primary -> FALSE
primary -> NULL
primary -> path
primary -> call
primary -> t_call
primary -> provider_call
primary -> ref_call
primary -> slice_call
primary -> proto_call
primary -> map
primary -> LPAREN expr RPAREN
primary -> LBRACK RBRACK
primary -> LBRACK value_list RBRACK

path -> IDENT
path -> path DOT IDENT
path -> path DOT NUMBER

call -> IDENT LPAREN RPAREN
call -> IDENT LPAREN arg_list RPAREN
arg_list -> expr
arg_list -> expr COMMA arg_list

t_call -> T LPAREN expr RPAREN
provider_call -> PROVIDER LPAREN expr RPAREN
provider_call -> PROVIDER LPAREN expr COMMA pair_list RPAREN
ref_call -> REF IDENT
ref_call -> REF LPAREN expr RPAREN
slice_call -> SLICE LPAREN arg_list RPAREN

proto_call -> BUTTON LPAREN expr RPAREN
"""

# A bare-expression grammar (for string-interpolation holes). When the grammar
# is given as text, langforge takes the start symbol from the ``start`` line and
# ignores any config override — so a separate text with ``start expr`` is needed.
EXPR_GRAMMAR = GRAMMAR.replace("start file", "start expr", 1)

