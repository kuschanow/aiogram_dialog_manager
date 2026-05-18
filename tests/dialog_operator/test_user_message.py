from aiogram_dialog_manager.instance.message import BotMessageRecord, UserMessageRecord


class TestAppendUserMessage:
    def test_appends_and_returns_record(self, operator, tg_message):
        record = operator.append_user_message(tg_message)
        assert isinstance(record, UserMessageRecord)
        assert operator.dialog.current_id is not None


class TestAppendBotMessage:
    def test_appends_record_to_tree(self, operator, tg_message):
        record = BotMessageRecord(type_name="t", menu=None, telegram_message_instance=tg_message)
        operator.append_bot_message(record)
        assert operator.dialog.current_id is not None
        assert operator.dialog.last_entry is record
