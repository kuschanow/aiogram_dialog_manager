from abc import ABC, abstractmethod
from typing import Optional, Any, Union

from aiogram import Bot
from aiogram.types import InputFile, Message
from pydantic import BaseModel, Field

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, AnyReplyMarkup, _BASE_MEDIA_PARAMS


class StickerExtraParams(BaseModel):
    emoji: Optional[str] = Field(None, description="Emoji associated with the sticker.")


class StickerMessagePrototype(BaseMessagePrototype, ABC):
    @abstractmethod
    async def get_sticker(self, dialog, context: Optional[dict[str, Any]]) -> Union[str, InputFile]:
        pass

    async def get_extra_params(self, dialog, context: Optional[dict[str, Any]]) -> StickerExtraParams:
        return StickerExtraParams()

    async def get_instance(self, dialog, context: Optional[dict[str, Any]]) -> BotMessageInstance:
        return BotMessageInstance(
            type_name=self.name,
            menu=await self.get_menu(dialog, context),
            data=await self.get_data(dialog, context),
            send_params=await self.get_send_params(dialog, context),
        )

    async def _do_send(
            self,
            bot: Bot,
            dialog,
            context: Optional[dict[str, Any]],
            target: MessageTarget,
            instance: BotMessageInstance,
            effective_params: SendParams,
            reply_markup: AnyReplyMarkup,
    ) -> Message:
        sticker = await self.get_sticker(dialog, context)
        extra = await self.get_extra_params(dialog, context)
        params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _BASE_MEDIA_PARAMS}
        return await bot.send_sticker(
            sticker=sticker,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **extra.model_dump(exclude_none=True),
            **params,
        )
