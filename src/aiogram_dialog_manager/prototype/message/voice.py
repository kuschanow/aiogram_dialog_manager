from abc import ABC, abstractmethod
from typing import Optional, Any, Union

from aiogram import Bot
from aiogram.types import InputFile, Message
from pydantic import BaseModel, Field

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import BaseCaptionMediaPrototype, AnyReplyMarkup, _CAPTION_MEDIA_PARAMS


class VoiceExtraParams(BaseModel):
    duration: Optional[int] = Field(None)


class VoiceMessagePrototype(BaseCaptionMediaPrototype, ABC):
    @abstractmethod
    async def get_voice(self, dialog, context: Optional[dict[str, Any]]) -> Union[str, InputFile]:
        pass

    async def get_extra_params(self, dialog, context: Optional[dict[str, Any]]) -> VoiceExtraParams:
        return VoiceExtraParams()

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
        voice = await self.get_voice(dialog, context)
        extra = await self.get_extra_params(dialog, context)
        params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _CAPTION_MEDIA_PARAMS}
        return await bot.send_voice(
            voice=voice,
            caption=instance.text,
            caption_entities=instance.entities,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **extra.model_dump(exclude_none=True),
            **params,
        )
