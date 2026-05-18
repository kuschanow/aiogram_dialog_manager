from aiogram_dialog_manager.dialog_manager import _find_button
from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import MenuInstance
from aiogram_dialog_manager.instance.message import BotMessageRecord, UserMessageRecord


class TestFindButton:
    def test_finds_button_in_current_branch(self, operator, tg_message):
        btn = ButtonInstance(text="OK", type_name="ok", id="btn_abc")
        menu = MenuInstance(type_name="m", buttons=[[btn]])
        record = BotMessageRecord(
            type_name="test",
            menu=menu,
            telegram_message_instance=tg_message,
        )
        operator.dialog.append_message(record)
        result = _find_button(operator.dialog, "btn_abc")
        assert result is not None
        msg_record, button = result
        assert button.id == "btn_abc"

    def test_returns_none_when_not_found(self, operator):
        result = _find_button(operator.dialog, "nonexistent_id")
        assert result is None

    def test_returns_none_for_user_messages(self, operator, tg_message):
        record = UserMessageRecord(telegram_message_instance=tg_message)
        operator.dialog.append_message(record)
        result = _find_button(operator.dialog, "some_btn")
        assert result is None

    def test_returns_none_for_bot_msg_without_menu(self, operator, tg_message):
        record = BotMessageRecord(
            type_name="test",
            menu=None,
            telegram_message_instance=tg_message,
        )
        operator.dialog.append_message(record)
        result = _find_button(operator.dialog, "some_btn")
        assert result is None
