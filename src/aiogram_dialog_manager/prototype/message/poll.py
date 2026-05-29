from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Any, Literal, Union, TYPE_CHECKING

from aiogram import Bot
from aiogram.types import Message, MessageEntity, InputPollOption
from pydantic import BaseModel, Field

from aiogram_dialog_manager.instance.message import BotMessageInstance, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, AnyReplyMarkup, _NO_SUGGESTED_POST_PARAMS

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


class PollExtraParams(BaseModel):
    question_parse_mode: Optional[str] = Field(None)
    question_entities: Optional[list[MessageEntity]] = Field(None)
    is_anonymous: Optional[bool] = Field(None)
    type: Optional[Literal["quiz", "regular"]] = Field(None)
    allows_multiple_answers: Optional[bool] = Field(None)
    correct_option_id: Optional[int] = Field(None)
    explanation: Optional[str] = Field(None)
    explanation_parse_mode: Optional[str] = Field(None)
    explanation_entities: Optional[list[MessageEntity]] = Field(None)
    open_period: Optional[int] = Field(None)
    close_date: Optional[Union[datetime, timedelta, int]] = Field(None)
    is_closed: Optional[bool] = Field(None)


class PollMessagePrototype(BaseMessagePrototype, ABC):
    @abstractmethod
    async def get_question(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> str:
        pass

    @abstractmethod
    async def get_options(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> list[Union[InputPollOption, str]]:
        pass

    async def get_extra_params(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> PollExtraParams:
        return PollExtraParams()

    async def get_instance(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> BotMessageInstance:
        return BotMessageInstance(
            type_name=self.name,
            text=await self.get_question(dialog, context),
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
        question = await self.get_question(dialog, context)
        options = await self.get_options(dialog, context)
        extra = await self.get_extra_params(dialog, context)
        params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _NO_SUGGESTED_POST_PARAMS}
        return await bot.send_poll(
            question=question,
            options=options,
            reply_markup=reply_markup,
            **target.model_dump(exclude_none=True),
            **extra.model_dump(exclude_none=True),
            **params,
        )
