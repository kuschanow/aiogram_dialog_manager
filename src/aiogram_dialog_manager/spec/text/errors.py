"""Errors raised while parsing a textual dialog spec."""
from __future__ import annotations

from typing import Optional

from aiogram_dialog_manager.spec.errors import SpecError


class DSLError(SpecError):
    """Base class for textual-DSL errors (a kind of :class:`SpecError`)."""


class DSLSyntaxError(DSLError):
    """The source text is lexically or grammatically invalid, or a construct
    is well-formed but semantically rejected during the tree transform."""

    def __init__(self, message: str, *, line: Optional[int] = None, col: Optional[int] = None):
        self.line = line
        self.col = col
        if line is not None:
            message = f"{message} (line {line}, col {col})" if col is not None else f"{message} (line {line})"
        super().__init__(message)
