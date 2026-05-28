from abc import ABC, abstractmethod
from typing import Optional, Any, ClassVar, TYPE_CHECKING

from aiogram_dialog_manager.instance.button import ButtonInstance, ButtonAdditionalParameters, InlineButtonAdditionalParameters

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class ButtonPrototype(ABC):
    _registry: ClassVar[dict[str, type]] = {}

    def __init_subclass__(cls, type_name: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if type_name is not None:
            if type_name in ButtonPrototype._registry:
                existing = ButtonPrototype._registry[type_name]
                raise ValueError(
                    f"ButtonPrototype name '{type_name}' is already registered by {existing.__qualname__}"
                )
            ButtonPrototype._registry[type_name] = cls
            cls._prototype_name = type_name

    @property
    def name(self) -> str:
        return self.__class__._prototype_name

    @abstractmethod
    async def get_state(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> str:
        pass

    async def get_data(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> dict:
        return context or {}

    async def get_inline_additional_parameters(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> Optional[InlineButtonAdditionalParameters]:
        return None

    async def get_common_additional_parameters(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> Optional[ButtonAdditionalParameters]:
        return None

    async def get_instance(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> ButtonInstance:
        state = await self.get_state(dialog, context)
        data = await self.get_data(dialog, context)
        inline_additional_parameters = await self.get_inline_additional_parameters(dialog, context)
        common_additional_parameters = await self.get_common_additional_parameters(dialog, context)
        return ButtonInstance(
            text=state,
            type_name=self.name,
            data=data,
            inline_additional_parameters=inline_additional_parameters,
            common_additional_parameters=common_additional_parameters
        )

    def __str__(self):
        return f"{self.__class__.__name__}(name={self.name})"
