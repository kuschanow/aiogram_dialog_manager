from abc import ABC, abstractmethod
from typing import Optional, Any, TYPE_CHECKING

from aiogram import Bot
from aiogram.types import Message
from pydantic import BaseModel, Field

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, AnyReplyMarkup, _BASE_MEDIA_PARAMS

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class ContactExtraParams(BaseModel):
    last_name: Optional[str] = Field(None)
    vcard: Optional[str] = Field(None, description="Additional data about the contact in the form of a vCard, 0-2048 bytes.")


class ContactMessagePrototype(BaseMessagePrototype, ABC):
    @abstractmethod
    async def get_phone_number(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> str:
        pass

    @abstractmethod
    async def get_first_name(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> str:
        pass

    async def get_extra_params(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> ContactExtraParams:
        return ContactExtraParams()

    async def get_instance(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> BotMessageInstance:
        return BotMessageInstance(
            type_name=self.name,
            menu=await self.get_menu(dialog, context),
            data=await self.get_data(dialog, context),
            send_params=await self.get_send_params(dialog, context),
        )

    async def _do_send(
            self,
            bot: Bot,
            dialog: "DialogOperator",
            context: Optional[dict[str, Any]],
            target: MessageTarget,
            instance: BotMessageInstance,
            effective_params: SendParams,
            reply_markup: AnyReplyMarkup,
    ) -> Message:
        phone_number = await self.get_phone_number(dialog, context)
        first_name = await self.get_first_name(dialog, context)
        extra = await self.get_extra_params(dialog, context)
        params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _BASE_MEDIA_PARAMS}
        return await bot.send_contact(
            phone_number=phone_number,
            first_name=first_name,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **extra.model_dump(exclude_none=True),
            **params,
        )
