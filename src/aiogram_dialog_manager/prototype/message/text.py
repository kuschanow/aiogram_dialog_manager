from abc import abstractmethod, ABC
from typing import Optional, Any, Union, TYPE_CHECKING

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import (
    BaseMessagePrototype,
    TextContent,
    AnyReplyMarkup,
    _EDIT_COMPATIBLE_PARAMS,
)

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class TextMessagePrototype(BaseMessagePrototype, ABC):
    @abstractmethod
    async def get_text_content(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> TextContent:
        pass

    async def get_instance(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> BotMessageInstance:
        text_content = await self.get_text_content(dialog, context)
        return BotMessageInstance(
            type_name=self.name,
            text=text_content.text,
            entities=text_content.entities,
            menu=await self.get_menu(dialog, context),
            data=await self.get_data(dialog, context),
            send_params=await self.get_send_params(dialog, context),
        )

    async def _do_edit(
            self,
            bot: Bot,
            dialog: "DialogOperator",
            context: Optional[dict[str, Any]],
            tg: Message,
            instance: BotMessageInstance,
            inline_markup: Optional[InlineKeyboardMarkup],
            effective_params: SendParams,
    ) -> Union[Message, bool]:
        edit_params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _EDIT_COMPATIBLE_PARAMS}
        return await bot.edit_message_text(
            chat_id=tg.chat.id,
            message_id=tg.message_id,
            text=instance.text,
            entities=instance.entities,
            reply_markup=inline_markup,
            business_connection_id=tg.business_connection_id,
            **edit_params,
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
        return await bot.send_message(
            text=instance.text,
            entities=instance.entities,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **effective_params.model_dump(exclude_unset=True),
        )
