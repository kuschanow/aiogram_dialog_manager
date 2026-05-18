from abc import ABC, abstractmethod
from typing import Optional, Any, ClassVar, TYPE_CHECKING

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import MenuInstance, AdditionalReplyMenuParameters

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class MenuPrototype(ABC):
    _registry: ClassVar[dict[str, type]] = {}

    def __init_subclass__(cls, type_name: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if type_name is not None:
            if type_name in MenuPrototype._registry:
                existing = MenuPrototype._registry[type_name]
                raise ValueError(
                    f"MenuPrototype name '{type_name}' is already registered by {existing.__qualname__}"
                )
            MenuPrototype._registry[type_name] = cls
            cls._prototype_name = type_name

    @property
    def name(self) -> str:
        return self.__class__._prototype_name

    @abstractmethod
    async def get_buttons(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> list[list[ButtonInstance]]:
        pass

    async def get_data(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> dict:
        return {}

    async def get_additional_reply_parameters(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> Optional[AdditionalReplyMenuParameters]:
        return None

    async def get_instance(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> MenuInstance:
        buttons = await self.get_buttons(dialog, context)
        data = await self.get_data(dialog, context)
        additional_reply_parameters = await self.get_additional_reply_parameters(dialog, context)
        return MenuInstance(
            type_name=self.name,
            buttons=buttons,
            data=data,
            additional_reply_parameters=additional_reply_parameters
        )

    def __str__(self):
        return f"{self.__class__.__name__}(name={self.name})"
