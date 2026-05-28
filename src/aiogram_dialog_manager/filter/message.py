from typing import Optional, Union

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from aiogram_dialog_manager.instance.message import BotMessageRecord
from aiogram_dialog_manager.prototype import BaseMessagePrototype


class MessageFilter(Filter):
    def __init__(self, *messages: Union[BaseMessagePrototype, str], **data):
        self.message_names = tuple(
            m.name if isinstance(m, BaseMessagePrototype) else m for m in messages
        )
        self.data = data

    async def __call__(self, callback: CallbackQuery, message_record: Optional[BotMessageRecord] = None):
        return (message_record is not None
                and (not self.message_names or message_record.type_name in self.message_names)
                and set(self.data.items()).issubset(set(message_record.data.items())))
