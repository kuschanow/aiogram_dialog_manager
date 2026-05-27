from typing import Optional, Union

from aiogram.filters import Filter
from aiogram.types import TelegramObject

from aiogram_dialog_manager.instance.menu import AnyMenuInstance
from aiogram_dialog_manager.prototype.menu import MenuPrototype


class MenuFilter(Filter):
    def __init__(self, menu: Union[MenuPrototype, str], **data):
        self.menu = menu
        self.data = data

    async def __call__(self, event: TelegramObject, menu: Optional[AnyMenuInstance] = None):
        name = self.menu.name if isinstance(self.menu, MenuPrototype) else self.menu
        return (menu is not None
                and menu.type_name == name
                and set(self.data.items()).issubset(set(menu.data.items())))
