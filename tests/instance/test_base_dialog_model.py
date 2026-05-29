import pytest
from aiogram.client.default import Default

from aiogram_dialog_manager.instance.base import (
    _DEFAULT_MARKER,
    _default_fallback,
    _strip_markers,
)
from aiogram_dialog_manager.instance.message import SendParams


class TestStripMarkers:
    def test_strips_marker_from_dict_value(self):
        result = _strip_markers({"a": _DEFAULT_MARKER, "b": "keep"})
        assert result == {"b": "keep"}

    def test_strips_marker_from_list_item(self):
        result = _strip_markers([_DEFAULT_MARKER, "keep"])
        assert result == ["keep"]

    def test_passes_through_scalar(self):
        assert _strip_markers("hello") == "hello"
        assert _strip_markers(42) == 42
        assert _strip_markers(None) is None

    def test_recursive_dict(self):
        result = _strip_markers({"outer": {"inner": _DEFAULT_MARKER, "keep": 1}})
        assert result == {"outer": {"keep": 1}}

    def test_recursive_list(self):
        result = _strip_markers([[_DEFAULT_MARKER, "keep"]])
        assert result == [["keep"]]


class TestDefaultFallback:
    def test_returns_marker_for_default(self):
        assert _default_fallback(Default("parse_mode")) == _DEFAULT_MARKER

    def test_raises_for_unknown_type(self):
        class Unknown:
            pass
        with pytest.raises(TypeError):
            _default_fallback(Unknown())


class TestBaseDialogModelJsonMode:
    def test_default_fields_excluded(self):
        params = SendParams()
        dumped = params.model_dump(mode="json")
        assert "parse_mode" not in dumped
        assert "protect_content" not in dumped

    def test_explicit_values_included(self):
        params = SendParams(parse_mode="HTML", disable_notification=True)
        dumped = params.model_dump(mode="json")
        assert dumped["parse_mode"] == "HTML"
        assert dumped["disable_notification"] is True

    def test_python_mode_preserves_defaults(self):
        params = SendParams()
        dumped = params.model_dump()
        assert isinstance(dumped["parse_mode"], Default)