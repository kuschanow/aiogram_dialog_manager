"""String literals and interpolation (grammar decisions D6, D11.4).

A ``STRING`` token holds the raw quoted text (either quote style). This module
turns it into a spec value:

- no ``{...}`` holes  -> a plain Python ``str`` (a literal Value);
- with holes          -> a list of fragments ``[str, node, str, ...]`` that the
  core concatenates at render time (``TextContentSpec`` / button text join).

``{{`` and ``}}`` are literal braces; ``{ expr }`` is an interpolation hole whose
text is handed to ``parse_expr``. Inside a hole, use the *other* quote style (or
a backslash-escaped quote) — an unescaped same-style quote would end the token
at the lexer level.
"""
from __future__ import annotations

from typing import Callable, Union

from aiogram_dialog_manager.spec.node import SpecNode
from aiogram_dialog_manager.spec.text.errors import DSLSyntaxError

Fragment = Union[str, SpecNode]

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "{": "{", "}": "}"}


def unquote_raw(token_value: str) -> str:
    """The raw inner text of a ``STRING`` token (quotes stripped)."""
    return token_value[1:-1]


def _decode_escape(ch: str) -> str:
    return _ESCAPES.get(ch, ch)


def _scan_hole(text: str, start: int) -> tuple[str, int]:
    """From ``text[start]`` (just past ``{``), return (hole_text, index_past_}).

    Tracks brace depth and skips over quoted substrings so a ``}`` inside a
    string literal in the expression does not close the hole.
    """
    depth = 1
    i = start
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'":
            quote = ch
            i += 1
            while i < n and text[i] != quote:
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    raise DSLSyntaxError("unterminated '{' interpolation in string")


def parse_string(
    token_value: str,
    parse_expr: Callable[[str], SpecNode],
) -> Fragment | list[Fragment]:
    """Turn a raw ``STRING`` token into a plain string or a fragment list."""
    raw = unquote_raw(token_value)
    fragments: list[Fragment] = []
    buf: list[str] = []
    i = 0
    n = len(raw)

    def flush() -> None:
        if buf:
            fragments.append("".join(buf))
            buf.clear()

    while i < n:
        ch = raw[i]
        if ch == "\\" and i + 1 < n:
            buf.append(_decode_escape(raw[i + 1]))
            i += 2
            continue
        if ch == "{":
            if i + 1 < n and raw[i + 1] == "{":
                buf.append("{")
                i += 2
                continue
            hole_text, i = _scan_hole(raw, i + 1)
            if not hole_text.strip():
                raise DSLSyntaxError("empty '{}' interpolation in string")
            flush()
            fragments.append(parse_expr(hole_text))
            continue
        if ch == "}":
            if i + 1 < n and raw[i + 1] == "}":
                buf.append("}")
                i += 2
                continue
            raise DSLSyntaxError("unmatched '}' in string (use '}}' for a literal)")
        buf.append(ch)
        i += 1

    flush()
    if not fragments:
        return ""
    if len(fragments) == 1 and isinstance(fragments[0], str):
        return fragments[0]
    return fragments
