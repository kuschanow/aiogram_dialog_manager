import logging
from typing import Optional, Any, Callable, Awaitable, Dict

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery

from aiogram_dialog_manager.instance.dialog import DialogInstance
from aiogram_dialog_manager.instance.menu import MenuInstance
from aiogram_dialog_manager.instance.message import BotMessageRecord
from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.dialog_operator import DialogOperator
from aiogram_dialog_manager.prototype.dialog import DialogPrototype
from aiogram_dialog_manager.storage.base import BaseStorage

logger = logging.getLogger(__name__)

UserMessageFilter = Callable[[Message], bool]


def _find_button(instance: DialogInstance, button_id: str) -> Optional[tuple[BotMessageRecord, ButtonInstance]]:
    for msg in reversed(instance.entries):
        if isinstance(msg, BotMessageRecord) and isinstance(msg.menu, MenuInstance):
            for row in msg.menu.buttons:
                for btn in row:
                    if btn.id == button_id:
                        return msg, btn
    return None


class DialogManager:
    def __init__(self, storage: BaseStorage):
        self._storage = storage
        self._user_message_filters: dict[str, UserMessageFilter] = {}

    def set_user_message_filter(self, dialog: "DialogPrototype | str", filter_fn: UserMessageFilter) -> None:
        type_name = dialog if isinstance(dialog, str) else dialog.name
        self._user_message_filters[type_name] = filter_fn

    async def create_dialog(
        self,
        prototype: DialogPrototype,
        user_id: int,
        chat_id: int,
        bot: Bot,
        context: Optional[dict[str, Any]] = None,
    ) -> DialogOperator:
        instance = await prototype.get_instance(user_id, chat_id, context)
        operator = DialogOperator(instance, bot)
        await self.save(operator)
        return operator

    async def get_dialog(self, dialog_id: str, bot: Bot) -> Optional[DialogOperator]:
        data = await self._storage.get_dict(f"dialog:{dialog_id}")
        if data is None:
            return None
        instance = DialogInstance.model_validate(data)
        return DialogOperator(instance, bot)

    async def get_active_dialog(self, user_id: int, chat_id: int, bot: Bot) -> Optional[DialogOperator]:
        dialog_id = await self._storage.get_string(f"active:{user_id}:{chat_id}")
        if dialog_id is None:
            return None
        return await self.get_dialog(dialog_id, bot)

    async def set_active_dialog(self, operator: DialogOperator) -> None:
        instance = operator.dialog
        await self._storage.set(f"active:{instance.user_id}:{instance.chat_id}", instance.id)

    async def save(self, operator: DialogOperator) -> None:
        instance = operator.dialog
        await self._storage.set(f"dialog:{instance.id}", instance.model_dump(mode="json"))
        for node in instance.nodes.values():
            msg = node.message
            if isinstance(msg, BotMessageRecord) and isinstance(msg.menu, MenuInstance):
                for row in msg.menu.buttons:
                    for btn in row:
                        await self._storage.set_value_with_index(f"button:{btn.id}", instance.id)

    async def delete(self, operator: DialogOperator) -> None:
        instance = operator.dialog
        button_keys = await self._storage.get_keys_by_value(instance.id)
        for key in button_keys:
            await self._storage.remove(key)
        await self._storage.remove_index(instance.id)
        active_key = f"active:{instance.user_id}:{instance.chat_id}"
        current_active = await self._storage.get_string(active_key)
        if current_active == instance.id:
            await self._storage.remove(active_key)
        await self._storage.remove(f"dialog:{instance.id}")

    def setup(self, dp: Dispatcher) -> None:
        dp.message.outer_middleware.register(self._message_middleware)
        dp.callback_query.outer_middleware.register(self._callback_middleware)

    async def _message_middleware(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        message: Message,
        data: Dict[str, Any],
    ) -> Any:
        bot: Bot = data["bot"]
        operator = None
        if message.from_user:
            operator = await self.get_active_dialog(message.from_user.id, message.chat.id, bot)

        if operator is not None and operator.dialog.config.save_user_message_nodes:
            filter_fn = self._user_message_filters.get(operator.dialog.type_name)
            if filter_fn is None or filter_fn(message):
                operator.append_user_message(message)

        data["dialog"] = operator
        data["dialog_manager"] = self

        result = await handler(message, data)

        if operator is not None and await self._storage.exists(f"dialog:{operator.dialog.id}"):
            await self.save(operator)

        return result

    async def _callback_middleware(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        callback: CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        bot: Bot = data["bot"]
        operator = None
        button = None
        message_record = None
        menu = None

        if callback.data and callback.data.startswith("b:"):
            button_id = callback.data[2:]
            dialog_id = await self._storage.get_string(f"button:{button_id}")
            if dialog_id:
                operator = await self.get_dialog(dialog_id, bot)
                if operator:
                    found = _find_button(operator.dialog, button_id)
                    if found:
                        message_record, button = found
                        menu = message_record.menu
                    else:
                        operator = None

        data["dialog"] = operator
        data["button"] = button
        data["message_record"] = message_record
        data["menu"] = menu
        data["dialog_manager"] = self

        result = await handler(callback, data)

        if operator is not None and await self._storage.exists(f"dialog:{operator.dialog.id}"):
            await self.save(operator)

        return result