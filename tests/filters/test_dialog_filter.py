from unittest.mock import MagicMock

from aiogram_dialog_manager.filter.dialog import DialogFilter
from tests.helpers import StubDialog


class TestDialogFilter:
    async def test_passes_when_dialog_matches_name(self, operator):
        f = DialogFilter("test")
        assert await f(MagicMock(), dialog=operator) is True

    async def test_passes_when_no_names_specified(self, operator):
        f = DialogFilter()
        assert await f(MagicMock(), dialog=operator) is True

    async def test_fails_when_dialog_is_none(self):
        f = DialogFilter("test")
        assert await f(MagicMock(), dialog=None) is False

    async def test_fails_when_name_does_not_match(self, operator):
        f = DialogFilter("other_dialog")
        assert await f(MagicMock(), dialog=operator) is False

    async def test_passes_with_matching_data(self, operator):
        operator.data["key"] = "value"
        f = DialogFilter("test", key="value")
        assert await f(MagicMock(), dialog=operator) is True

    async def test_fails_with_non_matching_data(self, operator):
        f = DialogFilter("test", key="wrong")
        assert await f(MagicMock(), dialog=operator) is False

    async def test_passes_with_multiple_names(self, operator):
        f = DialogFilter("other", "test")
        assert await f(MagicMock(), dialog=operator) is True

    async def test_passes_with_prototype_instance(self, operator):
        proto = StubDialog(name="test")
        f = DialogFilter(proto)
        assert await f(MagicMock(), dialog=operator) is True

    async def test_fails_with_non_matching_prototype(self, operator):
        proto = StubDialog(name="other")
        f = DialogFilter(proto)
        assert await f(MagicMock(), dialog=operator) is False
