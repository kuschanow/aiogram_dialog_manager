from typing import Optional, TYPE_CHECKING

from aiogram.filters import Filter
from aiogram.types import TelegramObject

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class DialogAccessFilter(Filter):
    async def __call__(self, event: TelegramObject, dialog: Optional["DialogOperator"] = None):
        return dialog is not None and dialog.user_id == event.from_user.id