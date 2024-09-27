from collections import ChainMap
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message

from aiogram_dialog_manager.instance.message import MessageInstance
from aiogram_dialog_manager.prototype import MenuPrototype


class Dialog:
    def __init__(self,
                 name: str,
                 user_id: int,
                 date: datetime,
                 dialog_id: str,
                 chat_id: int,
                 data: Dict[str, Any],
                 bot: Bot,
                 get_state_from_reply: bool = True,
                 messages: Optional[List[MessageInstance]] = None):
        self.name = name
        self.user_id = user_id
        self.date = date
        self.dialog_id = dialog_id
        self.chat_id = chat_id
        self.data = data
        self.temp = {}
        self.messages = {message.message_id: message for message in messages}
        self.bot = bot
        self.get_state_from_reply = get_state_from_reply

    @property
    def values(self) -> ChainMap[str, Any]:
        return ChainMap(self.temp, self.data)

    def add_user_message_to_dialog(self, message: Message) -> MessageInstance:
        if message.from_user.id == self.bot.id:
            raise Exception("You cannot add a bot message to a conversation. To do this, send a message through a dialogue instance.")

        dialog_message = MessageInstance(message_id=message.message_id, text=message.text, date=message.date, user_id=message.from_user.id)
        self.messages[message.message_id] = dialog_message
        return dialog_message

    async def send_message(self, text: str, menu: Optional[MenuPrototype] = None, menu_data: Optional[Dict[str, Any]] = None, message_marks: Optional[Dict[str, Any]] = None, **kwargs) -> Message:
        menu = await menu.get_instance(self, **(menu_data or {})) if menu else None

        message = await self.bot.send_message(
            chat_id=self.chat_id,
            text=text % self.values,
            reply_markup=menu.get_inline_keyboard() if menu else None,
            **kwargs)

        self.messages[message.message_id] = MessageInstance(
            date=message.date,
            message_id=message.message_id,
            user_id=message.from_user.id,
            text=message.text,
            menu=menu,
            marks=message_marks
        )

        return message
    
    async def edit_message(self, message_id: int, text: str, menu: Optional[MenuPrototype] = None, menu_data: Optional[Dict[str, Any]] = None, message_marks: Optional[Dict[str, Any]] = None, **kwargs) -> Message:
        if message_id not in self.messages:
            raise Exception("The message should be part of the dialogue")

        menu = await menu.get_instance(self, **(menu_data or {})) if menu else None

        telegram_message = await self.bot.edit_message_text(
            chat_id=self.chat_id,
            message_id=message_id,
            text=text % self.values,
            reply_markup=menu.get_inline_keyboard() if menu else None,
            **kwargs)

        self.messages[telegram_message.message_id].text = telegram_message.text
        self.messages[telegram_message.message_id].menu = menu
        self.messages[telegram_message.message_id].marks.update(message_marks or {})

        return telegram_message
        
    async def edit_keyboard(self, message_id: int, menu: MenuPrototype, menu_data: Optional[Dict[str, Any]] = None, message_marks: Optional[Dict[str, Any]] = None, **kwargs) -> Message:
        if message_id not in self.messages:
            raise Exception("The message should be part of the dialogue")

        menu = await menu.get_instance(self, **(menu_data or {}))

        telegram_message = await self.bot.edit_message_reply_markup(
            chat_id=self.chat_id,
            message_id=message_id,
            reply_markup=menu.get_inline_keyboard(),
            **kwargs)

        self.messages[telegram_message.message_id].menu = menu
        self.messages[telegram_message.message_id].marks.update(message_marks or {})

        return telegram_message

    async def delete_message(self, message_id: int, request_timeout: int | None=None):
        if message_id not in self.messages:
            raise Exception("The message should be part of the dialogue")

        await self.bot.delete_message(chat_id=self.chat_id, message_id=message_id, request_timeout=request_timeout)

        self.messages.pop(message_id)

    async def delete_all_messages(self, request_timeout: Optional[int] = None):
        for message_id in [m_id for m_id, _ in self.messages.items()]:
            await self.delete_message(message_id, request_timeout)

    async def set_state(self, state: State, relayed_message: MessageInstance | None=None, context: FSMContext | None=None):
        if relayed_message and relayed_message not in self.messages.values():
            raise Exception("The message should be part of the dialogue")

        if context:
            await context.set_state(state)
            await context.set_data({"dialog_id": self.dialog_id})

        if relayed_message:
            relayed_message.marks["state"] = str(state)
        else:
            self.messages[max(self.messages)].marks["state"] = str(state)

    async def remove_state(self, state: Optional[State] = None, relayed_message_id: Optional[int] = None, context: Optional[FSMContext] = None):
        if relayed_message_id and relayed_message_id not in self.messages:
            raise Exception("The message should be part of the dialogue")

        if context:
            await context.clear()
        if relayed_message_id:
            self.messages[relayed_message_id].marks.pop("state")
        else:
            for message in self.messages.values():
                if "state" in message.marks:
                    if state and message.marks["state"] != str(state):
                        continue
                    message.marks.pop("state")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "user_id": self.user_id,
            "date": self.date.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "chat_id": self.chat_id,
            "data": self.data,
            "messages": [message.to_dict() for _, message in self.messages.items()],
            "get_state_from_reply": self.get_state_from_reply
        }

    @staticmethod
    def create(name: str, user_id: int, chat_id: int, bot: Bot, get_state_from_reply: bool = True):
        return Dialog(
            name=name,
            user_id=user_id,
            chat_id=chat_id,
            date=datetime.now(),
            dialog_id=str(uuid4()),
            data={},
            messages=[],
            bot=bot,
            get_state_from_reply=get_state_from_reply
        )

    @staticmethod
    def from_dict(data: Dict[str, Any], dialog_id: str, bot: Bot) -> 'Dialog':
        return Dialog(
            name=data["name"],
            user_id=data["user_id"],
            date=datetime.strptime(data["date"], "%Y-%m-%d %H:%M:%S.%f"),
            dialog_id=dialog_id,
            chat_id=data["chat_id"],
            data=data["data"],
            messages=[MessageInstance.from_dict(message) for message in data["messages"]],
            bot=bot,
            get_state_from_reply=data["get_state_from_reply"]
        )
