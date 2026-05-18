from abc import ABC, abstractmethod
from typing import Optional, Any, Union

from aiogram import Bot
from aiogram.types import InputFile, InputMediaDocument, Message
from pydantic import BaseModel, ConfigDict, Field

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import InputMediaPrototype, AnyReplyMarkup, _CAPTION_MEDIA_PARAMS


class DocumentExtraParams(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    thumbnail: Optional[InputFile] = Field(None, description="Thumbnail of the file sent.")
    disable_content_type_detection: Optional[bool] = Field(None, description="Disables automatic server-side content type detection.")


class DocumentMessagePrototype(InputMediaPrototype, ABC):
    @abstractmethod
    async def get_document(self, dialog, context: Optional[dict[str, Any]]) -> Union[str, InputFile]:
        pass

    async def get_extra_params(self, dialog, context: Optional[dict[str, Any]]) -> DocumentExtraParams:
        return DocumentExtraParams()

    async def get_input_media(self, dialog, context: Optional[dict[str, Any]], parse_mode=None) -> InputMediaDocument:
        extra = await self.get_extra_params(dialog, context)
        text_content = await self.get_text_content(dialog, context)
        return InputMediaDocument(
            media=await self.get_document(dialog, context),
            thumbnail=extra.thumbnail,
            caption=text_content.text,
            parse_mode=parse_mode,
            caption_entities=text_content.entities,
            disable_content_type_detection=extra.disable_content_type_detection,
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
        document = await self.get_document(dialog, context)
        extra = await self.get_extra_params(dialog, context)
        params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _CAPTION_MEDIA_PARAMS}
        return await bot.send_document(
            document=document,
            caption=instance.text,
            caption_entities=instance.entities,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **extra.model_dump(exclude_none=True),
            **params,
        )
