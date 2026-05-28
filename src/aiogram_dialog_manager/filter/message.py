from typing import Optional

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from aiogram_dialog_manager.instance.message import BotMessageRecord
from aiogram_dialog_manager.prototype import BaseMessagePrototype


class MessageFilter(Filter):
    def __init__(self, message: BaseMessagePrototype, **data):
        self.message = message
        self.data = data

    async def __call__(self, callback: CallbackQuery, message_record: Optional[BotMessageRecord] = None):
        return (message_record is not None
                and message_record.type_name == self.message.name
                and set(self.data.items()).issubset(set(message_record.data.items())))
