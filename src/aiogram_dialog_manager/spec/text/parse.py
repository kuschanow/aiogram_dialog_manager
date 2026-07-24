"""Public entry point: parse textual dialog specs into :class:`DialogSpec`.

Parsing uses the pre-generated, self-contained lexer/parsers under
``_generated/`` (compiled from ``tools/_dsl_grammar.py`` by
``tools/gen_text_dsl.py``) — no ``langforge`` dependency at runtime. The two
parsers cover the whole ``file`` and a bare ``expr`` (string-interpolation holes).
"""
from __future__ import annotations

from aiogram_dialog_manager.spec.model import DialogSpec
from aiogram_dialog_manager.spec.node import SpecNode
from aiogram_dialog_manager.spec.text._generated.lexer import Lexer
from aiogram_dialog_manager.spec.text._generated.parser_expr import parse as _parse_expr_tree
from aiogram_dialog_manager.spec.text._generated.parser_file import parse as _parse_file_tree
from aiogram_dialog_manager.spec.text.errors import DSLSyntaxError
from aiogram_dialog_manager.spec.text.transform import Transformer

_lexer = Lexer()


def _tokenize(source: str) -> list:
    try:
        return list(_lexer.tokenize(source))
    except Exception as exc:  # the generated lexer raises on unrecognized input
        raise DSLSyntaxError(f"tokenization failed: {exc}") from exc


def parse_dialog_text(source: str) -> DialogSpec:
    """Parse a whole ``dialog { ... }`` unit into a :class:`DialogSpec`.

    The result is an ordinary spec model — feed it to
    :func:`aiogram_dialog_manager.spec.compile_dialog` to get prototypes.
    """
    tokens = _tokenize(source)
    try:
        tree = _parse_file_tree(tokens)
    except Exception as exc:
        raise DSLSyntaxError(f"parse failed: {exc}") from exc

    transformer = Transformer(parse_expr_text=lambda text: _parse_expr(text, transformer))
    return transformer.build(tree)


def _parse_expr(text: str, transformer: Transformer) -> SpecNode:
    """Parse a single expression (used for string-interpolation holes)."""
    tokens = [t for t in _tokenize(text) if t.type != "EOF"]
    if not tokens:
        raise DSLSyntaxError("empty expression")
    try:
        tree = _parse_expr_tree(tokens)
    except Exception as exc:
        raise DSLSyntaxError(f"invalid expression '{text.strip()}': {exc}") from exc
    return transformer._expr(tree)
