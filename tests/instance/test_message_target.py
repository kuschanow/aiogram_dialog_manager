from aiogram.types import Chat

from aiogram_dialog_manager.instance.message import MessageTarget
from tests.conftest import make_tg_message


class TestMessageTarget:
    def test_from_message_basic(self):
        msg = make_tg_message(chat_id=200)
        target = MessageTarget.from_message(msg)
        assert target.chat_id == 200
        assert target.message_thread_id is None
        assert target.business_connection_id is None

    def test_from_message_with_topic(self):
        msg = make_tg_message(is_topic=True, thread_id=5)
        target = MessageTarget.from_message(msg)
        assert target.message_thread_id == 5

    def test_from_message_with_business(self):
        msg = make_tg_message(business_connection_id="biz123")
        target = MessageTarget.from_message(msg)
        assert target.business_connection_id == "biz123"

    def test_from_chat(self):
        chat = Chat(id=999, type="group")
        target = MessageTarget.from_chat(chat)
        assert target.chat_id == 999


class TestMessageTargetSerialization:
    def test_basic_roundtrip(self):
        target = MessageTarget(chat_id=100)
        dumped = target.model_dump(mode="json")
        restored = MessageTarget.model_validate(dumped)
        assert restored.chat_id == 100
        assert restored.message_thread_id is None

    def test_full_roundtrip(self):
        target = MessageTarget(
            chat_id=100,
            message_thread_id=5,
            business_connection_id="biz",
            direct_messages_topic_id=7,
        )
        dumped = target.model_dump(mode="json")
        restored = MessageTarget.model_validate(dumped)
        assert restored.chat_id == 100
        assert restored.message_thread_id == 5
        assert restored.business_connection_id == "biz"
        assert restored.direct_messages_topic_id == 7
