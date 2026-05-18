from unittest.mock import MagicMock

from aiogram import Dispatcher

from aiogram_dialog_manager.dialog_manager import DialogManager
from aiogram_dialog_manager.storage.memory import MemoryStorage


class TestDialogManagerSetup:
    def test_setup_registers_middlewares(self):
        manager = DialogManager(MemoryStorage())
        dp = MagicMock(spec=Dispatcher)
        dp.message = MagicMock()
        dp.message.outer_middleware = MagicMock()
        dp.callback_query = MagicMock()
        dp.callback_query.outer_middleware = MagicMock()
        manager.setup(dp)
        dp.message.outer_middleware.register.assert_called_once()
        dp.callback_query.outer_middleware.register.assert_called_once()
