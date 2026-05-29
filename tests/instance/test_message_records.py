from aiogram.client.default import Default

from aiogram_dialog_manager.instance.message import BotMessageInstance, BotMessageRecord, SendParams, UserMessageRecord
from tests.conftest import make_tg_message


class TestUserMessageRecordSerialization:
    def test_roundtrip(self):
        msg = make_tg_message()
        record = UserMessageRecord(telegram_message_instance=msg)
        dumped = record.model_dump(mode="json")
        restored = UserMessageRecord.model_validate(dumped)
        assert restored.id == record.id
        assert restored.is_bot_message is False

    def test_with_data_roundtrip(self):
        msg = make_tg_message()
        record = UserMessageRecord(telegram_message_instance=msg, data={"key": "value"})
        dumped = record.model_dump(mode="json")
        restored = UserMessageRecord.model_validate(dumped)
        assert restored.data == {"key": "value"}


class TestBotMessageRecordSerialization:
    def test_roundtrip_with_default_send_params(self):
        msg = make_tg_message()
        record = BotMessageRecord(type_name="test", telegram_message_instance=msg)
        dumped = record.model_dump(mode="json")
        restored = BotMessageRecord.model_validate(dumped)
        assert restored.type_name == "test"
        assert isinstance(restored.send_params.parse_mode, Default)

    def test_roundtrip_with_custom_send_params(self):
        msg = make_tg_message()
        record = BotMessageRecord(
            type_name="test",
            telegram_message_instance=msg,
            send_params=SendParams(parse_mode="HTML", disable_notification=True),
        )
        dumped = record.model_dump(mode="json")
        restored = BotMessageRecord.model_validate(dumped)
        assert restored.send_params.parse_mode == "HTML"
        assert restored.send_params.disable_notification is True

    def test_with_data_roundtrip(self):
        msg = make_tg_message()
        record = BotMessageRecord(type_name="test", telegram_message_instance=msg, data={"x": 1})
        dumped = record.model_dump(mode="json")
        restored = BotMessageRecord.model_validate(dumped)
        assert restored.data == {"x": 1}


class TestBotMessageInstanceSerialization:
    def test_roundtrip(self):
        instance = BotMessageInstance(type_name="test", text="Hello")
        dumped = instance.model_dump(mode="json")
        restored = BotMessageInstance.model_validate(dumped)
        assert restored.type_name == "test"
        assert restored.text == "Hello"
        assert isinstance(restored.send_params.parse_mode, Default)

    def test_with_custom_send_params_roundtrip(self):
        instance = BotMessageInstance(
            type_name="test",
            send_params=SendParams(parse_mode="MarkdownV2"),
        )
        dumped = instance.model_dump(mode="json")
        restored = BotMessageInstance.model_validate(dumped)
        assert restored.send_params.parse_mode == "MarkdownV2"
