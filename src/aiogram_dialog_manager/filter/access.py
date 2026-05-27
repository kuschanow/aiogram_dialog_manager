from typing import Optional, TYPE_CHECKING

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class DialogAccessFilter(Filter):
    async def __call__(self, callback: CallbackQuery, dialog: Optional["DialogOperator"] = None):
        return dialog is not None and dialog.user_id == callback.from_user.id
