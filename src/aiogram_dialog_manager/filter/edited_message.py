from typing import Optional

from aiogram.filters import Filter
from aiogram.types import Message

from aiogram_dialog_manager.instance.message import UserMessageRecord


class EditedMessageFilter(Filter):
    def __init__(self, **data):
        self.data = data

    async def __call__(self, message: Message, message_record: Optional[UserMessageRecord] = None):
        return (message_record is not None
                and set(self.data.items()).issubset(set(message_record.data.items())))
