from unittest.mock import MagicMock

from aiogram_dialog_manager.filter.access import DialogAccessFilter


class TestDialogAccessFilter:
    async def test_passes_when_user_matches(self, operator):
        event = MagicMock()
        event.from_user = MagicMock()
        event.from_user.id = operator.user_id
        f = DialogAccessFilter()
        assert await f(event, dialog=operator) is True

    async def test_fails_when_user_does_not_match(self, operator):
        event = MagicMock()
        event.from_user = MagicMock()
        event.from_user.id = 9999
        f = DialogAccessFilter()
        assert await f(event, dialog=operator) is False

    async def test_fails_when_dialog_is_none(self):
        event = MagicMock()
        event.from_user = MagicMock()
        event.from_user.id = 42
        f = DialogAccessFilter()
        assert await f(event, dialog=None) is False
