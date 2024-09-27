from typing import Optional

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from aiogram_dialog_manager import Dialog


class DialogFilter(Filter):
    def __init__(self, *dialog_names: str):
        self.dialog_names = dialog_names

    async def __call__(self, callback: CallbackQuery, dialog: Optional[Dialog] = None):
        return dialog and dialog.name in self.dialog_names
