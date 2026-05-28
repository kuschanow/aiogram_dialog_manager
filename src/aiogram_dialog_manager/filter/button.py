from typing import Optional, Union

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.prototype.button import ButtonPrototype


class ButtonFilter(Filter):
    def __init__(self, *buttons: Union[ButtonPrototype, str], **data):
        self.button_names = tuple(
            b.name if isinstance(b, ButtonPrototype) else b for b in buttons
        )
        self.data = data

    async def __call__(self, callback: CallbackQuery, button: Optional[ButtonInstance] = None):
        return (button is not None
                and (not self.button_names or button.type_name in self.button_names)
                and set(self.data.items()).issubset(set(button.data.items())))
