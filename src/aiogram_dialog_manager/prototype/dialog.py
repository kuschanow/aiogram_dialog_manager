import uuid
from abc import ABC, abstractmethod
from typing import Optional, Any, ClassVar

from aiogram_dialog_manager.instance.dialog import DialogInstance, DialogConfig


class DialogPrototype(ABC):
    _registry: ClassVar[dict[str, type]] = {}

    def __init_subclass__(cls, type_name: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if type_name is not None:
            if type_name in DialogPrototype._registry:
                existing = DialogPrototype._registry[type_name]
                raise ValueError(
                    f"DialogPrototype name '{type_name}' is already registered by {existing.__qualname__}"
                )
            DialogPrototype._registry[type_name] = cls
            cls._prototype_name = type_name

    @property
    def name(self) -> str:
        return self.__class__._prototype_name

    async def get_data(self, context: Optional[dict[str, Any]]) -> dict:
        return context or {}

    async def get_config(self) -> DialogConfig:
        return DialogConfig()

    async def get_instance(self, user_id: int, chat_id: int, context: Optional[dict[str, Any]] = None) -> DialogInstance:
        data = await self.get_data(context) or {}
        config = await self.get_config()
        snap_id = uuid.uuid4().hex
        return DialogInstance(
            type_name=self.name,
            user_id=user_id,
            chat_id=chat_id,
            data=data.copy(),
            snapshots={snap_id: data.copy()},
            initial_snapshot_id=snap_id,
            config=config,
        )

    def __str__(self):
        return f"{self.__class__.__name__}(name={self.name})"
