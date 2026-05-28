from typing import Optional, Union

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from aiogram_dialog_manager.instance.menu import AnyMenuInstance
from aiogram_dialog_manager.prototype.menu import MenuPrototype


class MenuFilter(Filter):
    def __init__(self, *menus: Union[MenuPrototype, str], **data):
        self.menu_names = tuple(
            m.name if isinstance(m, MenuPrototype) else m for m in menus
        )
        self.data = data

    async def __call__(self, callback: CallbackQuery, menu: Optional[AnyMenuInstance] = None):
        return (menu is not None
                and (not self.menu_names or menu.type_name in self.menu_names)
                and set(self.data.items()).issubset(set(menu.data.items())))
