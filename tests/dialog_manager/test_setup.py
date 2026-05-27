from unittest.mock import MagicMock

from aiogram import Dispatcher

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.storage.memory import MemoryStorage

_OBSERVERS = [
    "message",
    "edited_message",
    "callback_query",
    "my_chat_member",
    "chat_member",
    "poll_answer",
    "message_reaction",
]


class TestDialogManagerSetup:
    def test_setup_registers_middlewares(self):
        manager = DialogManager(MemoryStorage())
        dp = MagicMock(spec=Dispatcher)
        for name in _OBSERVERS:
            observer = MagicMock()
            observer.outer_middleware = MagicMock()
            setattr(dp, name, observer)

        manager.setup(dp)

        for name in _OBSERVERS:
            getattr(dp, name).outer_middleware.register.assert_called_once()