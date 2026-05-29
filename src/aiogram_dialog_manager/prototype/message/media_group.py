from abc import ABC, abstractmethod
from typing import Optional, Any, Union, TYPE_CHECKING

from aiogram import Bot
from aiogram.types import InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo, Message

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, AnyReplyMarkup, _NO_SUGGESTED_POST_PARAMS

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator

MediaGroupItem = Union[InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo]


class MediaGroupMessagePrototype(BaseMessagePrototype, ABC):
    @abstractmethod
    async def get_media(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> list[MediaGroupItem]:
        pass

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
        media = await self.get_media(dialog, context)
        params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _NO_SUGGESTED_POST_PARAMS}
        messages = await bot.send_media_group(
            media=media,
            **target.model_dump(exclude_none=True),
            **params,
        )
        return messages[0]
