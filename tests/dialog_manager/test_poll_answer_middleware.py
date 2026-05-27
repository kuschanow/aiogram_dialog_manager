from datetime import datetime, timezone
from unittest.mock import MagicMock

from aiogram.types import Chat, Message, Poll, PollAnswer, PollOption, User

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.instance.message import BotMessageRecord
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubDialog


def make_manager() -> tuple[DialogManager, MemoryStorage]:
    storage = MemoryStorage()
    return DialogManager(storage), storage


def make_poll_answer(poll_id: str = "poll123") -> MagicMock:
    answer = MagicMock(spec=PollAnswer)
    answer.poll_id = poll_id
    return answer


def make_poll_message(poll_id: str = "poll123", message_id: int = 5, chat_id: int = 100) -> Message:
    poll = Poll(
        id=poll_id,
        question="Best color?",
        options=[
            PollOption(text="Red", voter_count=0),
            PollOption(text="Blue", voter_count=0),
        ],
        total_voter_count=0,
        is_closed=False,
        is_anonymous=True,
        type="regular",
        allows_multiple_answers=False,
    )
    return Message(
        message_id=message_id,
        date=datetime.now(timezone.utc),
        chat=Chat(id=chat_id, type="private"),
        from_user=User(id=1, is_bot=True, first_name="Bot"),
        poll=poll,
    )


class TestPollAnswerMiddleware:
    async def test_injects_dialog_and_message_record_when_poll_indexed(self, mock_bot, tg_message):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)

        poll_msg = make_poll_message()
        record = BotMessageRecord(type_name="poll", telegram_message_instance=poll_msg)
        op.dialog.append_message(record)
        await manager.save(op)

        captured = {}

        async def handler(answer, data):
            captured["dialog"] = data.get("dialog")
            captured["message_record"] = data.get("message_record")
            captured["dialog_manager"] = data.get("dialog_manager")

        await manager._poll_answer_middleware(handler, make_poll_answer("poll123"), {"bot": mock_bot})
        assert captured["dialog"] is not None
        assert captured["dialog"].dialog.id == op.dialog.id
        assert isinstance(captured["message_record"], BotMessageRecord)
        assert captured["message_record"].telegram_message_instance.poll.id == "poll123"
        assert captured["dialog_manager"] is manager

    async def test_injects_none_when_poll_not_indexed(self, mock_bot):
        manager, _ = make_manager()

        captured = {}

        async def handler(answer, data):
            captured["dialog"] = data.get("dialog")
            captured["message_record"] = data.get("message_record")

        await manager._poll_answer_middleware(handler, make_poll_answer("unknown_poll"), {"bot": mock_bot})
        assert captured["dialog"] is None
        assert captured["message_record"] is None

    async def test_saves_dialog_after_handler(self, mock_bot):
        manager, _ = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)

        poll_msg = make_poll_message()
        record = BotMessageRecord(type_name="poll", telegram_message_instance=poll_msg)
        op.dialog.append_message(record)
        await manager.save(op)

        async def handler(answer, data):
            data["dialog"].data["answered"] = True

        await manager._poll_answer_middleware(handler, make_poll_answer("poll123"), {"bot": mock_bot})
        loaded = await manager.get_dialog(op.dialog.id, mock_bot)
        assert loaded.data.get("answered") is True

    async def test_injects_none_message_record_when_poll_removed_from_dialog(self, mock_bot):
        manager, storage = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)

        poll_msg = make_poll_message()
        record = BotMessageRecord(type_name="poll", telegram_message_instance=poll_msg)
        op.dialog.append_message(record)
        await manager.save(op)

        op.dialog.nodes.clear()
        await storage.set(f"dialog:{op.dialog.id}", op.dialog.model_dump(mode="json"))

        captured = {}

        async def handler(answer, data):
            captured["dialog"] = data.get("dialog")
            captured["message_record"] = data.get("message_record")

        await manager._poll_answer_middleware(handler, make_poll_answer("poll123"), {"bot": mock_bot})
        assert captured["dialog"] is not None
        assert captured["message_record"] is None

    async def test_does_not_save_if_dialog_deleted(self, mock_bot):
        manager, storage = make_manager()
        op = await manager.create_dialog(StubDialog(), 42, 100, mock_bot)

        poll_msg = make_poll_message()
        record = BotMessageRecord(type_name="poll", telegram_message_instance=poll_msg)
        op.dialog.append_message(record)
        await manager.save(op)

        async def handler(answer, data):
            await manager.delete(data["dialog"])

        await manager._poll_answer_middleware(handler, make_poll_answer("poll123"), {"bot": mock_bot})
        assert not await storage.exists(f"dialog:{op.dialog.id}")