import inspect
from typing import Callable, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram_dialog_manager.instance import MenuInstance
    from aiogram_dialog_manager import Dialog


class MenuPrototype:
    def __init__(self, get_keyboard: Callable):
        self.get_keyboard = get_keyboard

    def _get_relevant_kwargs(self, **kwargs) -> Dict[str, Any]:
        func_args = inspect.signature(self.get_keyboard).parameters
        relevant_kwargs = {k: v for k, v in kwargs.items() if k in func_args}
        return relevant_kwargs

    async def get_instance(self, dialog: Optional['Dialog'] = None, **kwargs) -> 'MenuInstance':
        from aiogram_dialog_manager.instance import MenuInstance

        relevant_kwargs = self._get_relevant_kwargs(dialog=dialog, **kwargs)
        keyboard = self.get_keyboard(**relevant_kwargs)

        if inspect.isawaitable(keyboard):
            keyboard = await keyboard

        return MenuInstance(keyboard)
