from typing import Optional

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from aiogram_dialog_manager import Dialog


class DialogDataFilter(Filter):
    def __init__(self, **data):
         self.data = data or {}

    async def __call__(self, callback: CallbackQuery, dialog: Optional[Dialog] = None):
        return dialog and set(self.data.items()).issubset(set(dialog.data.items()))
