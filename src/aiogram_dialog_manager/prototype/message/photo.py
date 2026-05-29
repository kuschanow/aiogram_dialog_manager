from abc import ABC, abstractmethod
from typing import Optional, Any, Union, TYPE_CHECKING

from aiogram import Bot
from aiogram.types import InputFile, InputMediaPhoto, Message
from pydantic import BaseModel, Field

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import InputMediaPrototype, AnyReplyMarkup, _CAPTION_MEDIA_PARAMS

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class PhotoExtraParams(BaseModel):
    has_spoiler: Optional[bool] = Field(None, description="Pass True if the photo needs to be covered with a spoiler animation.")
    show_caption_above_media: Optional[bool] = Field(None, description="Pass True if the caption must be shown above the message media.")


class PhotoMessagePrototype(InputMediaPrototype, ABC):
    @abstractmethod
    async def get_photo(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> Union[str, InputFile]:
        pass

    async def get_extra_params(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> PhotoExtraParams:
        return PhotoExtraParams()

    async def get_input_media(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]], parse_mode=None) -> InputMediaPhoto:
        extra = await self.get_extra_params(dialog, context)
        text_content = await self.get_text_content(dialog, context)
        return InputMediaPhoto(
            media=await self.get_photo(dialog, context),
            caption=text_content.text,
            parse_mode=parse_mode,
            caption_entities=text_content.entities,
            has_spoiler=extra.has_spoiler,
            show_caption_above_media=extra.show_caption_above_media,
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
        photo = await self.get_photo(dialog, context)
        extra = await self.get_extra_params(dialog, context)
        params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _CAPTION_MEDIA_PARAMS}
        return await bot.send_photo(
            photo=photo,
            caption=instance.text,
            caption_entities=instance.entities,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **extra.model_dump(exclude_none=True),
            **params,
        )
