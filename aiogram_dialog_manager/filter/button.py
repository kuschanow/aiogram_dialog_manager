from typing import Optional

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from aiogram_dialog_manager.instance import ButtonInstance
from aiogram_dialog_manager.prototype import ButtonPrototype


class ButtonFilter(Filter):
    def __init__(self, button: ButtonPrototype|str, **data):
        self.button = button
        self.data = data or {}

    async def __call__(self, callback: CallbackQuery, button: Optional[ButtonInstance] = None):
        return (button
                and button.type_name == (self.button.name if isinstance(self.button, ButtonPrototype) else self.button)
                and set(self.data.items()).issubset(set(button.data.items())))
