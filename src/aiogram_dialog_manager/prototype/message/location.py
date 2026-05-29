from abc import ABC, abstractmethod
from typing import Optional, Any, TYPE_CHECKING

from aiogram import Bot
from aiogram.types import Message
from pydantic import BaseModel, Field

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, AnyReplyMarkup, _BASE_MEDIA_PARAMS

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class LocationExtraParams(BaseModel):
    horizontal_accuracy: Optional[float] = Field(None, description="The radius of uncertainty for the location, measured in meters; 0-1500.")
    live_period: Optional[int] = Field(None, description="Period in seconds during which the location will be updated.")
    heading: Optional[int] = Field(None, description="Direction in which the user is moving, in degrees; 1-360.")
    proximity_alert_radius: Optional[int] = Field(None, description="Maximum distance for proximity alerts, in meters; 1-100000.")


class LocationMessagePrototype(BaseMessagePrototype, ABC):
    @abstractmethod
    async def get_latitude(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> float:
        pass

    @abstractmethod
    async def get_longitude(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> float:
        pass

    async def get_extra_params(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> LocationExtraParams:
        return LocationExtraParams()

    async def get_instance(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> BotMessageInstance:
        return BotMessageInstance(
            type_name=self.name,
            menu=await self.get_menu(dialog, context),
            data=await self.get_data(dialog, context),
            send_params=await self.get_send_params(dialog, context),
        )

    async def _do_send(
            self,
            bot: Bot,
            dialog: "Optional[DialogOperator]",
            context: Optional[dict[str, Any]],
            target: MessageTarget,
            instance: BotMessageInstance,
            effective_params: SendParams,
            reply_markup: AnyReplyMarkup,
    ) -> Message:
        latitude = await self.get_latitude(dialog, context)
        longitude = await self.get_longitude(dialog, context)
        extra = await self.get_extra_params(dialog, context)
        params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _BASE_MEDIA_PARAMS}
        return await bot.send_location(
            latitude=latitude,
            longitude=longitude,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **extra.model_dump(exclude_none=True),
            **params,
        )
