from unittest.mock import MagicMock

from aiogram.types import Message

from aiogram_dialog_manager.filter.edited_message import EditedMessageFilter
from aiogram_dialog_manager.instance.message import UserMessageRecord


def make_record(data: dict | None = None) -> UserMessageRecord:
    msg = MagicMock(spec=Message)
    msg.message_id = 1
    return UserMessageRecord(telegram_message_instance=msg, data=data or {})


class TestEditedMessageFilter:
    async def test_passes_when_record_found(self):
        f = EditedMessageFilter()
        assert await f(MagicMock(), message_record=make_record()) is True

    async def test_fails_when_record_is_none(self):
        f = EditedMessageFilter()
        assert not await f(MagicMock(), message_record=None)

    async def test_passes_with_matching_data(self):
        record = make_record(data={"step": "confirm"})
        f = EditedMessageFilter(step="confirm")
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_with_non_matching_data(self):
        record = make_record(data={"step": "confirm"})
        f = EditedMessageFilter(step="other")
        assert not await f(MagicMock(), message_record=record)

    async def test_fails_when_record_is_none_with_data(self):
        f = EditedMessageFilter(step="confirm")
        assert not await f(MagicMock(), message_record=None)

    async def test_passes_with_subset_data(self):
        record = make_record(data={"step": "confirm", "extra": "value"})
        f = EditedMessageFilter(step="confirm")
        assert await f(MagicMock(), message_record=record) is True
