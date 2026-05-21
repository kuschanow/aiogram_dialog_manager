import logging
import uuid
from typing import Optional, Any, Callable, Awaitable, Dict

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyMarkupUnion
from pydantic import TypeAdapter

from aiogram_dialog_manager.instance.dialog import DialogInstance
from aiogram_dialog_manager.instance.menu import MenuInstance, AnyMenuInstance
from aiogram_dialog_manager.instance.message import BotMessageRecord
from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.dialog_operator import DialogOperator
from aiogram_dialog_manager.prototype.dialog import DialogPrototype
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from aiogram_dialog_manager.storage.base import BaseStorage

logger = logging.getLogger(__name__)

UserMessageFilter = Callable[[Message], bool]
DeadButtonHandler = Callable[[CallbackQuery], Awaitable[None]]

_UNSET = object()

_AnyMenuInstanceAdapter = TypeAdapter(AnyMenuInstance)


def _find_button(instance: DialogInstance, button_id: str) -> Optional[tuple[BotMessageRecord, ButtonInstance]]:
    for msg in reversed(instance.entries):
        if isinstance(msg, BotMessageRecord) and isinstance(msg.menu, MenuInstance):
            for row in msg.menu.buttons:
                for btn in row:
                    if btn.id == button_id:
                        return msg, btn
    return None


class DialogManager:
    def __init__(
        self,
        storage: BaseStorage,
        dialog_ttl: Optional[int] = None,
        standalone_menu_ttl: Optional[int] = None,
    ):
        self._storage = storage
        self._dialog_ttl = dialog_ttl
        self._standalone_menu_ttl = standalone_menu_ttl
        self._user_message_filters: dict[str, UserMessageFilter] = {}
        self._dead_button_handler: Optional[DeadButtonHandler] = None

    def set_user_message_filter(self, dialog: "DialogPrototype | str", filter_fn: UserMessageFilter) -> None:
        type_name = dialog if isinstance(dialog, str) else dialog.name
        self._user_message_filters[type_name] = filter_fn

    def set_dead_button_handler(self, handler: DeadButtonHandler) -> None:
        self._dead_button_handler = handler

    async def create_dialog(
        self,
        prototype: DialogPrototype,
        user_id: int,
        chat_id: int,
        bot: Bot,
        context: Optional[dict[str, Any]] = None,
        ttl: Optional[int] = _UNSET,
    ) -> DialogOperator:
        instance = await prototype.get_instance(user_id, chat_id, context)
        operator = DialogOperator(instance, bot)
        effective_ttl = self._dialog_ttl if ttl is _UNSET else ttl
        await self.save(operator, ttl=effective_ttl)
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

    async def save(self, operator: DialogOperator, ttl: Optional[int] = _UNSET) -> None:
        instance = operator.dialog
        effective_ttl = self._dialog_ttl if ttl is _UNSET else ttl
        await self._storage.set(f"dialog:{instance.id}", instance.model_dump(mode="json"), ttl=effective_ttl)
        active_key = f"active:{instance.user_id}:{instance.chat_id}"
        if await self._storage.get_string(active_key) == instance.id:
            await self._storage.set(active_key, instance.id, ttl=effective_ttl)
        for node in instance.nodes.values():
            msg = node.message
            if isinstance(msg, BotMessageRecord) and isinstance(msg.menu, MenuInstance):
                for row in msg.menu.buttons:
                    for btn in row:
                        await self._storage.set_value_with_index(f"button:{btn.id}", instance.id, ttl=effective_ttl)

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

    async def create_standalone_menu(
        self,
        proto: MenuPrototype,
        context: Optional[dict[str, Any]] = None,
        ttl: Optional[int] = _UNSET,
    ) -> tuple[str, ReplyMarkupUnion]:
        effective_ttl = self._standalone_menu_ttl if ttl is _UNSET else ttl
        menu_id = uuid.uuid4().hex
        instance = await proto.get_instance(None, context)
        await self._storage.set(f"standalone:{menu_id}", instance.model_dump(mode="json"), ttl=effective_ttl)
        if isinstance(instance, MenuInstance):
            for row in instance.buttons:
                for btn in row:
                    await self._storage.set_value_with_index(f"sbutton:{btn.id}", menu_id, ttl=effective_ttl)
        return menu_id, instance.get_markup()

    async def delete_standalone_menu(self, menu_id: str) -> None:
        button_keys = await self._storage.get_keys_by_value(menu_id)
        for key in button_keys:
            await self._storage.remove(key)
        await self._storage.remove_index(menu_id)
        await self._storage.remove(f"standalone:{menu_id}")

    async def cleanup_orphaned(self) -> int:
        count = 0
        for key in await self._storage.get_range_of_keys("dialog:"):
            data = await self._storage.get_dict(key)
            if data is None:
                continue
            instance = DialogInstance.model_validate(data)
            current_active = await self._storage.get_string(f"active:{instance.user_id}:{instance.chat_id}")
            if current_active != instance.id:
                for bkey in await self._storage.get_keys_by_value(instance.id):
                    await self._storage.remove(bkey)
                await self._storage.remove_index(instance.id)
                await self._storage.remove(key)
                count += 1
        for key in await self._storage.get_range_of_keys("standalone:"):
            menu_id = key.split("standalone:")[1]
            if not await self._storage.get_keys_by_value(menu_id):
                await self._storage.remove(key)
                count += 1
        return count

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
            else:
                menu_id = await self._storage.get_string(f"sbutton:{button_id}")
                if menu_id:
                    menu_data = await self._storage.get_dict(f"standalone:{menu_id}")
                    if menu_data:
                        standalone_menu = _AnyMenuInstanceAdapter.validate_python(menu_data)
                        if isinstance(standalone_menu, MenuInstance):
                            for row in standalone_menu.buttons:
                                for btn in row:
                                    if btn.id == button_id:
                                        button = btn
                                        menu = standalone_menu

            if button is None and self._dead_button_handler is not None:
                await self._dead_button_handler(callback)

        data["dialog"] = operator
        data["button"] = button
        data["message_record"] = message_record
        data["menu"] = menu
        data["dialog_manager"] = self

        result = await handler(callback, data)

        if operator is not None and await self._storage.exists(f"dialog:{operator.dialog.id}"):
            await self.save(operator)

        return result