"""Translation extraction from dialog spec models.

Two complementary paths cover the two places ``t`` msgids live:

- **Builder code** (``.py``): standard pybabel keyword extraction —
  ``pybabel extract -k t ...`` picks up ``b.t("msgid")`` calls.
- **Serialized models** (JSON in files or a DB dump): the keyword mechanism
  cannot see ``{"type": "t", "key": ...}`` nodes, so this module ships a
  Babel extractor (registered via the ``babel.extractors`` entry point as
  ``aiogram_dialog_spec``) plus :func:`iter_translation_keys` for custom
  pipelines over models loaded from anywhere.
"""
import json
from typing import Any, BinaryIO, Iterator, Union

from pydantic import BaseModel

from aiogram_dialog_manager.spec.nodes import TranslateNode


def iter_translation_keys(spec: Union[BaseModel, dict, list]) -> Iterator[str]:
    """Yield every ``t`` msgid inside a model or its canonical dict form.

    Accepts a :class:`~aiogram_dialog_manager.spec.model.DialogSpec` (or any
    pydantic model containing spec nodes) as well as a raw dict/list. Order is
    document order; duplicates are preserved (gettext catalogs deduplicate).
    """
    if isinstance(spec, BaseModel):
        from aiogram_dialog_manager.spec.compile import iter_spec_nodes
        for node in iter_spec_nodes(spec):
            if isinstance(node, TranslateNode):
                yield node.key
    elif isinstance(spec, dict):
        if spec.get("type") == "t" and isinstance(spec.get("key"), str):
            yield spec["key"]
        for value in spec.values():
            yield from iter_translation_keys(value)
    elif isinstance(spec, (list, tuple)):
        for item in spec:
            yield from iter_translation_keys(item)


def _line_of(lines: list[str], key: str, start: int) -> tuple[int, int]:
    """Best-effort line lookup: the first line at or after ``start`` containing
    the JSON-encoded msgid. Returns ``(lineno, next_start)``; 1-based lineno,
    falling back to line 1 when the literal is not found (e.g. minified)."""
    needles = {json.dumps(key), json.dumps(key, ensure_ascii=False)}
    for index in range(start, len(lines)):
        if any(needle in lines[index] for needle in needles):
            return index + 1, index
    return 1, start


def extract_spec(
        fileobj: BinaryIO,
        keywords: Any = None,
        comment_tags: Any = None,
        options: Any = None,
) -> Iterator[tuple[int, None, str, list]]:
    """Babel extractor for JSON files with serialized dialog specs.

    Wire it up in a pybabel mapping file::

        [aiogram_dialog_spec: dialogs/**.json]

    Yields ``(lineno, funcname, message, comments)`` tuples; line numbers are
    best-effort (the line where the msgid literal occurs in the source).
    """
    encoding = (options or {}).get("encoding", "utf-8")
    source = fileobj.read()
    if isinstance(source, bytes):
        source = source.decode(encoding)
    payload = json.loads(source)
    lines = source.splitlines()
    next_start: dict[str, int] = {}
    for key in iter_translation_keys(payload):
        lineno, found_at = _line_of(lines, key, next_start.get(key, 0))
        # Repeated msgids advance past the previous occurrence so each yield
        # points at its own line.
        next_start[key] = found_at + 1
        yield lineno, None, key, []
