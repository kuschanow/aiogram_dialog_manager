from abc import ABC, abstractmethod
from typing import Optional, Any, Union, TYPE_CHECKING

from aiogram import Bot
from aiogram.types import InputFile, InputMediaAnimation, Message
from pydantic import BaseModel, ConfigDict, Field

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import InputMediaPrototype, AnyReplyMarkup, _CAPTION_MEDIA_PARAMS

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class AnimationExtraParams(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    duration: Optional[int] = Field(None)
    width: Optional[int] = Field(None)
    height: Optional[int] = Field(None)
    thumbnail: Optional[InputFile] = Field(None)
    has_spoiler: Optional[bool] = Field(None)
    show_caption_above_media: Optional[bool] = Field(None)


class AnimationMessagePrototype(InputMediaPrototype, ABC):
    @abstractmethod
    async def get_animation(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> Union[str, InputFile]:
        pass

    async def get_extra_params(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> AnimationExtraParams:
        return AnimationExtraParams()

    async def get_input_media(self, dialog: "DialogOperator", context: Optional[dict[str, Any]], parse_mode=None) -> InputMediaAnimation:
        extra = await self.get_extra_params(dialog, context)
        text_content = await self.get_text_content(dialog, context)
        return InputMediaAnimation(
            media=await self.get_animation(dialog, context),
            thumbnail=extra.thumbnail,
            caption=text_content.text,
            parse_mode=parse_mode,
            caption_entities=text_content.entities,
            width=extra.width,
            height=extra.height,
            duration=extra.duration,
            has_spoiler=extra.has_spoiler,
            show_caption_above_media=extra.show_caption_above_media,
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
        animation = await self.get_animation(dialog, context)
        extra = await self.get_extra_params(dialog, context)
        params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _CAPTION_MEDIA_PARAMS}
        return await bot.send_animation(
            animation=animation,
            caption=instance.text,
            caption_entities=instance.entities,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **extra.model_dump(exclude_none=True),
            **params,
        )
