from typing import Optional, Union, TYPE_CHECKING

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from aiogram_dialog_manager.prototype.dialog import DialogPrototype

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class DialogFilter(Filter):
    def __init__(self, *dialogs: Union[DialogPrototype, str], **data):
        self.dialog_names = tuple(
            d.name if isinstance(d, DialogPrototype) else d for d in dialogs
        )
        self.data = data

    async def __call__(self, callback: CallbackQuery, dialog: Optional["DialogOperator"] = None):
        return (dialog is not None
                and (not self.dialog_names or dialog.name in self.dialog_names)
                and set(self.data.items()).issubset(set(dialog.data.items())))