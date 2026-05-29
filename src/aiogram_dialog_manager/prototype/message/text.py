from abc import abstractmethod, ABC
from typing import Optional, Any, TYPE_CHECKING

from aiogram import Bot
from aiogram.types import Message

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, TextContent, AnyReplyMarkup

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class TextMessagePrototype(BaseMessagePrototype, ABC):
    @abstractmethod
    async def get_text_content(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> TextContent:
        pass

    async def get_instance(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> BotMessageInstance:
        text_content = await self.get_text_content(dialog, context)
        return BotMessageInstance(
            type_name=self.name,
            text=text_content.text,
            entities=text_content.entities,
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
        return await bot.send_message(
            text=instance.text,
            entities=instance.entities,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **effective_params.model_dump(exclude_unset=True),
        )
