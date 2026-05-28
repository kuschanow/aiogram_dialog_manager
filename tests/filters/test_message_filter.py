from unittest.mock import MagicMock

from aiogram.types import Message

from aiogram_dialog_manager.filter.message import MessageFilter
from aiogram_dialog_manager.instance.message import BotMessageRecord
from tests.helpers import StubText, StubPhoto


def make_record(type_name: str = "text_msg", data: dict | None = None) -> BotMessageRecord:
    msg = MagicMock(spec=Message)
    msg.message_id = 1
    return BotMessageRecord(type_name=type_name, telegram_message_instance=msg, data=data or {})


class TestMessageFilter:
    async def test_passes_when_type_name_matches(self):
        record = make_record("text_msg")
        f = MessageFilter(StubText())
        assert await f(MagicMock(), message_record=record) is True

    async def test_passes_with_string_name(self):
        record = make_record("text_msg")
        f = MessageFilter("text_msg")
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_when_record_is_none(self):
        f = MessageFilter(StubText())
        assert not await f(MagicMock(), message_record=None)

    async def test_fails_when_type_name_does_not_match(self):
        record = make_record("photo_msg")
        f = MessageFilter(StubText())
        assert not await f(MagicMock(), message_record=record)

    async def test_passes_with_matching_data(self):
        record = make_record("text_msg", data={"step": "confirm"})
        f = MessageFilter(StubText(), step="confirm")
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_with_non_matching_data(self):
        record = make_record("text_msg", data={"step": "confirm"})
        f = MessageFilter(StubText(), step="other")
        assert not await f(MagicMock(), message_record=record)

    async def test_passes_with_subset_data(self):
        record = make_record("text_msg", data={"step": "confirm", "extra": "value"})
        f = MessageFilter(StubText(), step="confirm")
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_when_record_is_none_with_data(self):
        f = MessageFilter(StubText(), step="confirm")
        assert not await f(MagicMock(), message_record=None)

    async def test_fails_when_type_matches_but_data_missing(self):
        record = make_record("text_msg", data={})
        f = MessageFilter(StubText(), step="confirm")
        assert not await f(MagicMock(), message_record=record)

    async def test_passes_when_no_protos_specified(self):
        f = MessageFilter()
        record = make_record("any_msg")
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_when_no_protos_and_record_is_none(self):
        f = MessageFilter()
        assert not await f(MagicMock(), message_record=None)

    async def test_passes_with_multiple_protos_first_matches(self):
        record = make_record("text_msg")
        f = MessageFilter(StubText(), StubPhoto())
        assert await f(MagicMock(), message_record=record) is True

    async def test_passes_with_multiple_protos_second_matches(self):
        record = make_record("photo_msg")
        f = MessageFilter(StubText(), StubPhoto())
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_with_multiple_protos_none_matches(self):
        record = make_record("video_msg")
        f = MessageFilter(StubText(), StubPhoto())
        assert not await f(MagicMock(), message_record=record)

    async def test_passes_with_multiple_string_names(self):
        record = make_record("photo_msg")
        f = MessageFilter("text_msg", "photo_msg")
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_with_multiple_string_names_none_matches(self):
        record = make_record("video_msg")
        f = MessageFilter("text_msg", "photo_msg")
        assert not await f(MagicMock(), message_record=record)

    async def test_passes_with_multiple_protos_and_matching_data(self):
        record = make_record("photo_msg", data={"step": "confirm"})
        f = MessageFilter(StubText(), StubPhoto(), step="confirm")
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_with_multiple_protos_matching_type_but_wrong_data(self):
        record = make_record("photo_msg", data={"step": "other"})
        f = MessageFilter(StubText(), StubPhoto(), step="confirm")
        assert not await f(MagicMock(), message_record=record)

    async def test_passes_with_mixed_proto_and_string(self):
        record = make_record("video_msg")
        f = MessageFilter(StubText(), "video_msg")
        assert await f(MagicMock(), message_record=record) is True
