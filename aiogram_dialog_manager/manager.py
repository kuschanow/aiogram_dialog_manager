from typing import Dict, Callable, Any, Awaitable

from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery

from aiogram_dialog_manager.dialog import Dialog
from aiogram_dialog_manager.storage import BaseStorage


class DialogManager:
    def __init__(self, storage: BaseStorage, router: Router, bot: Bot):
        self.storage = storage
        self.bot = bot

        router.message.outer_middleware.register(self.message_outer_middleware)
        router.callback_query.outer_middleware.register(self.callback_outer_middleware)

        self.router = router

    async def get_dialog(self, dialog_data: Dict, dialog_id: str) -> Dialog:
        return Dialog.from_dict(dialog_data, dialog_id, self.bot)

    async def save_dialog(self, instance: Dialog):
        await self.storage.set(f"dialog:{instance.dialog_id}", instance.to_dict())
        for _, message in instance.messages.items():
            await self.storage.set_value_with_index(f"message_info:{instance.chat_id}:{message.message_id}", instance.dialog_id)

    async def delete_dialog(self, instance: Dialog):
        related_messages = await self.storage.get_keys_by_value(instance.dialog_id)
        for message in related_messages:
            await self.storage.remove(message)
        await self.storage.remove_index(instance.dialog_id)
        await self.storage.remove(f"dialog:{instance.dialog_id}")

    async def message_outer_middleware(self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        message: Message,
        data: Dict[str, Any]
    ) -> Any:
        state_data = await data["state"].get_data()
        dialog_data = {"data": None, "id": None}
        if "dialog_id" in state_data:
            dialog_data = {"data": await self.storage.get_dict(f"dialog:{state_data['dialog_id']}"), "id": state_data['dialog_id']}
        elif message.reply_to_message:
            message_info = await self.storage.get_string(f"message_info:{message.chat.id}:{message.reply_to_message.message_id}")
            if message_info:
                dialog_data = {"data": await self.storage.get_dict(f"dialog:{message_info}"), "id": message_info}

        if dialog_data["id"] and dialog_data["data"]:
            data["dialog"] = await self.get_dialog(dialog_data["data"], dialog_data["id"])

        data["dialog_manager"] = self

        result = await handler(message, data)
        if "dialog" in data and await self.storage.exists(f"dialog:{data['dialog'].dialog_id}"):
            await self.save_dialog(data["dialog"])
        return result

    async def callback_outer_middleware(self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        callback: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        message_info = await self.storage.get_string(f"message_info:{callback.message.chat.id}:{callback.message.message_id}")
        dialog_data = {"data": None, "id": None}
        if message_info:
            dialog_data = {"data": await self.storage.get_dict(f"dialog:{message_info}"), "id": message_info}

        if dialog_data["id"] and dialog_data["data"]:
            data["dialog"] = await self.get_dialog(dialog_data["data"], dialog_data["id"])
            data["dialog_message"] = data["dialog"].messages[callback.message.message_id]
            data["button"] = data["dialog"].messages[callback.message.message_id].menu.get_button_by_id(callback.data[2:])

        data["dialog_manager"] = self

        result = await handler(callback, data)
        if "dialog" in data and await self.storage.exists(f"dialog:{data['dialog'].dialog_id}"):
            await self.save_dialog(data["dialog"])
        return result
