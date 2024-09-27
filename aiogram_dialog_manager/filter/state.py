from typing import Optional

from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message

from aiogram_dialog_manager import Dialog


class StateFilter(Filter):
    def __init__(self, state: State):
        self.state = state

    async def __call__(self, event, state: FSMContext, dialog: Optional[Dialog] = None):
        if not dialog:
            return False

        if await state.get_state() == self.state:
            return True

        if not await state.get_state() and isinstance(event, Message) and dialog.get_state_from_reply:
            message = dialog.messages[event.reply_to_message.message_id]
            if "state" in message.marks:
                return message.marks["state"] == str(self.state)
            return False
