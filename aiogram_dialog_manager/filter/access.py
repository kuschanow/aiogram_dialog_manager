from typing import Optional

from aiogram.filters import Filter
from aiogram.types import TelegramObject

from aiogram_dialog_manager import Dialog


class DialogAccessFilter(Filter):
    async def __call__(self, event: TelegramObject, dialog: Optional[Dialog] = None):
        return dialog and dialog.user_id == event.from_user.id
