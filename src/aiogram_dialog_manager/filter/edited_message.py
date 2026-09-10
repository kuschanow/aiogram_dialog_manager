from typing import Optional

from aiogram.filters import Filter
from aiogram.types import Message

from aiogram_dialog_manager.filter._matching import data_matches
from aiogram_dialog_manager.instance.message import UserMessageRecord


class EditedMessageFilter(Filter):
    def __init__(self, **data):
        self.data = data

    async def __call__(self, message: Message, message_record: Optional[UserMessageRecord] = None):
        return (message_record is not None
                and data_matches(message_record.data, self.data))
