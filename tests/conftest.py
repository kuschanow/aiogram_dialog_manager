"""Shared fixtures for all test modules."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.types import Chat, Message, User

from aiogram_dialog_manager.dialog_operator import DialogOperator
from aiogram_dialog_manager.instance.dialog import DialogInstance
from aiogram_dialog_manager.storage.memory import MemoryStorage
from tests.helpers import StubDialog


def make_tg_message(
        message_id: int = 1,
        chat_id: int = 100,
        user_id: int = 42,
        is_topic: bool = False,
        thread_id: int | None = None,
        business_connection_id: str | None = None,
) -> Message:
    user = User(id=user_id, is_bot=False, first_name="Test")
    msg = Message(
        message_id=message_id,
        date=datetime.now(timezone.utc),
        chat=Chat(id=chat_id, type="private"),
        from_user=user,
        is_topic_message=is_topic if is_topic else None,
        message_thread_id=thread_id,
        business_connection_id=business_connection_id,
    )
    return msg


def make_dialog_instance(user_id: int = 42, chat_id: int = 100, type_name: str = "test") -> DialogInstance:
    prototype = StubDialog(name=type_name)
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        prototype.get_instance(user_id, chat_id)
    )


@pytest.fixture
def tg_message() -> Message:
    return make_tg_message()


@pytest.fixture
def mock_bot(tg_message) -> AsyncMock:
    bot = AsyncMock(spec=Bot)
    bot.send_message.return_value = tg_message
    bot.send_photo.return_value = tg_message
    bot.send_document.return_value = tg_message
    bot.send_video.return_value = tg_message
    bot.send_audio.return_value = tg_message
    bot.send_animation.return_value = tg_message
    bot.send_voice.return_value = tg_message
    bot.send_video_note.return_value = tg_message
    bot.send_sticker.return_value = tg_message
    bot.send_location.return_value = tg_message
    bot.send_contact.return_value = tg_message
    bot.send_poll.return_value = tg_message
    bot.send_media_group.return_value = [tg_message]
    bot.edit_message_text.return_value = tg_message
    bot.edit_message_caption.return_value = tg_message
    bot.edit_message_media.return_value = tg_message
    bot.edit_message_live_location.return_value = tg_message
    bot.edit_message_reply_markup.return_value = tg_message
    bot.delete_message.return_value = True
    return bot


@pytest.fixture
def dialog_instance() -> DialogInstance:
    return make_dialog_instance()


@pytest.fixture
def operator(dialog_instance, mock_bot) -> DialogOperator:
    return DialogOperator(dialog_instance, mock_bot)


@pytest.fixture
def memory_storage() -> MemoryStorage:
    return MemoryStorage()
