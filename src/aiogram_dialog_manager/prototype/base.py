from abc import ABC, abstractmethod
from typing import Optional, Any, ClassVar, Union

from aiogram import Bot
from aiogram.types import (
    Message, MessageEntity,
    InputMediaAnimation, InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo,
    InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply,
)
from pydantic import BaseModel

from aiogram_dialog_manager.instance.menu import AnyMenuInstance
from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget

AnyInputMedia = Union[InputMediaAnimation, InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo]
AnyReplyMarkup = Optional[InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply]

_CAPTION_MEDIA_PARAMS = frozenset({
    "parse_mode", "disable_notification", "protect_content", "allow_paid_broadcast",
    "message_effect_id", "suggested_post_parameters", "reply_parameters", "allow_sending_without_reply",
})
_BASE_MEDIA_PARAMS = _CAPTION_MEDIA_PARAMS - {"parse_mode"}
_NO_SUGGESTED_POST_PARAMS = _BASE_MEDIA_PARAMS - {"suggested_post_parameters"}


class TextContent(BaseModel):
    text: Optional[str] = None
    entities: Optional[list[MessageEntity]] = None


class BaseMessagePrototype(ABC):
    _registry: ClassVar[dict[str, type]] = {}

    def __init_subclass__(cls, type_name: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if type_name is not None:
            if type_name in BaseMessagePrototype._registry:
                existing = BaseMessagePrototype._registry[type_name]
                raise ValueError(
                    f"BaseMessagePrototype name '{type_name}' is already registered by {existing.__qualname__}"
                )
            BaseMessagePrototype._registry[type_name] = cls
            cls._prototype_name = type_name

    @property
    def name(self) -> str:
        return self.__class__._prototype_name

    async def get_menu(self, dialog, context: Optional[dict[str, Any]]) -> Optional[AnyMenuInstance]:
        return None

    async def get_data(self, dialog, context: Optional[dict[str, Any]]) -> dict:
        return {}

    async def get_send_params(self, dialog, context: Optional[dict[str, Any]]) -> SendParams:
        return SendParams()

    @abstractmethod
    async def get_instance(self, dialog, context: Optional[dict[str, Any]]) -> BotMessageInstance:
        pass

    @abstractmethod
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
        pass

    def __str__(self):
        return f"{self.__class__.__name__}(name={self.name})"


class BaseCaptionMediaPrototype(BaseMessagePrototype, ABC):
    async def get_text_content(self, dialog, context: Optional[dict[str, Any]]) -> TextContent:
        return TextContent()

    async def get_instance(self, dialog, context: Optional[dict[str, Any]]) -> BotMessageInstance:
        text_content = await self.get_text_content(dialog, context)
        return BotMessageInstance(
            type_name=self.name,
            text=text_content.text,
            entities=text_content.entities,
            menu=await self.get_menu(dialog, context),
            data=await self.get_data(dialog, context),
            send_params=await self.get_send_params(dialog, context),
        )


class InputMediaPrototype(BaseCaptionMediaPrototype):
    @abstractmethod
    async def get_input_media(self, dialog, context: Optional[dict[str, Any]], parse_mode=None) -> AnyInputMedia:
        ...
