"""Textual DSL for dialog specs — a superstructure over the JSON core.

``parse_dialog_text(source)`` turns the compact block syntax into an ordinary
:class:`~aiogram_dialog_manager.spec.model.DialogSpec`, which then compiles like
any other spec. See ``docs/dialog_spec_text_syntax.md`` for the grammar.
"""
from aiogram_dialog_manager.spec.text.errors import DSLError, DSLSyntaxError
from aiogram_dialog_manager.spec.text.parse import parse_dialog_text

__all__ = ["DSLError", "DSLSyntaxError", "parse_dialog_text"]
