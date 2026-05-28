from unittest.mock import MagicMock

from aiogram.types import Message

from aiogram_dialog_manager.filter.message import MessageFilter
from aiogram_dialog_manager.instance.message import BotMessageRecord


def make_record(type_name: str = "text_msg", data: dict | None = None) -> BotMessageRecord:
    msg = MagicMock(spec=Message)
    msg.message_id = 1
    return BotMessageRecord(type_name=type_name, telegram_message_instance=msg, data=data or {})


class StubProto:
    def __init__(self, name: str):
        self.name = name


class TestMessageFilter:
    async def test_passes_when_type_name_matches(self):
        proto = StubProto("text_msg")
        record = make_record("text_msg")
        f = MessageFilter(proto)
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_when_record_is_none(self):
        proto = StubProto("text_msg")
        f = MessageFilter(proto)
        assert not await f(MagicMock(), message_record=None)

    async def test_fails_when_type_name_does_not_match(self):
        proto = StubProto("text_msg")
        record = make_record("photo_msg")
        f = MessageFilter(proto)
        assert not await f(MagicMock(), message_record=record)

    async def test_passes_with_matching_data(self):
        proto = StubProto("text_msg")
        record = make_record("text_msg", data={"step": "confirm"})
        f = MessageFilter(proto, step="confirm")
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_with_non_matching_data(self):
        proto = StubProto("text_msg")
        record = make_record("text_msg", data={"step": "confirm"})
        f = MessageFilter(proto, step="other")
        assert not await f(MagicMock(), message_record=record)

    async def test_passes_with_subset_data(self):
        proto = StubProto("text_msg")
        record = make_record("text_msg", data={"step": "confirm", "extra": "value"})
        f = MessageFilter(proto, step="confirm")
        assert await f(MagicMock(), message_record=record) is True

    async def test_fails_when_record_is_none_with_data(self):
        proto = StubProto("text_msg")
        f = MessageFilter(proto, step="confirm")
        assert not await f(MagicMock(), message_record=None)

    async def test_fails_when_type_matches_but_data_missing(self):
        proto = StubProto("text_msg")
        record = make_record("text_msg", data={})
        f = MessageFilter(proto, step="confirm")
        assert not await f(MagicMock(), message_record=record)