import logging
from typing import Optional, Any, Literal

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, ReplyParameters, ReplyKeyboardMarkup, InlineKeyboardMarkup, ReplyKeyboardRemove, ForceReply

from aiogram_dialog_manager.instance.dialog import DialogInstance
from aiogram_dialog_manager.instance.message import AnyMessageRecord, BaseMessageRecord, BotMessageInstance, BotMessageRecord, UserMessageRecord, SendParams, MessageTarget
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, BaseCaptionMediaPrototype, InputMediaPrototype
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from aiogram_dialog_manager.prototype.message.animation import AnimationMessagePrototype
from aiogram_dialog_manager.prototype.message.audio import AudioMessagePrototype
from aiogram_dialog_manager.prototype.message.contact import ContactMessagePrototype
from aiogram_dialog_manager.prototype.message.document import DocumentMessagePrototype
from aiogram_dialog_manager.prototype.message.location import LocationMessagePrototype
from aiogram_dialog_manager.prototype.message.media_group import MediaGroupMessagePrototype
from aiogram_dialog_manager.prototype.message.photo import PhotoMessagePrototype
from aiogram_dialog_manager.prototype.message.poll import PollMessagePrototype
from aiogram_dialog_manager.prototype.message.sticker import StickerMessagePrototype
from aiogram_dialog_manager.prototype.message.text import TextMessagePrototype
from aiogram_dialog_manager.prototype.message.video import VideoMessagePrototype
from aiogram_dialog_manager.prototype.message.video_note import VideoNoteMessagePrototype
from aiogram_dialog_manager.prototype.message.voice import VoiceMessagePrototype

logger = logging.getLogger(__name__)

_EDIT_COMPATIBLE_PARAMS = frozenset({"parse_mode", "link_preview_options", "disable_web_page_preview"})
_EDIT_CAPTION_PARAMS = frozenset({"parse_mode"})


class DialogOperator:
    def __init__(self, dialog: DialogInstance, bot: Bot):
        self._dialog = dialog
        self._bot = bot
        self.temp: dict = {}

    @property
    def dialog(self) -> DialogInstance:
        return self._dialog

    @property
    def name(self) -> str:
        return self._dialog.type_name

    @property
    def user_id(self) -> int:
        return self._dialog.user_id

    @property
    def chat_id(self) -> int:
        return self._dialog.chat_id

    @property
    def data(self) -> dict:
        return self._dialog.data

    def append_user_message(self, message: Message, data: Optional[dict[str, Any]] = None) -> UserMessageRecord:
        record = UserMessageRecord(telegram_message_instance=message, data=data or {})
        self._dialog.append_message(record)
        return record

    def rollback(self, index: int) -> None:
        self._dialog.rollback(index)

    def switch_node(self, node_id: Optional[str]) -> None:
        self._dialog.switch_node(node_id)

    async def get_message_instance(self, message_prototype: BaseMessagePrototype, context: Optional[dict[str, Any]]) -> BotMessageInstance:
        instance = await message_prototype.get_instance(self, context)
        logger.debug(f"Got message instance %(instance)s for prototype %(message_prototype)s", instance, message_prototype)
        return instance

    async def _prepare_instance(
            self,
            message_prototype: BaseMessagePrototype,
            context: Optional[dict[str, Any]],
            send_params: Optional[SendParams],
            keyboard_type: Optional[Literal["inline", "reply"]],
    ) -> tuple[BotMessageInstance, SendParams, Optional[InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply]]:
        instance = await message_prototype.get_instance(self, context)

        effective_params = instance.send_params
        if send_params is not None:
            effective_params = instance.send_params.model_copy(
                update=send_params.model_dump(exclude_unset=True)
            )

        reply_markup = instance.menu.get_markup(keyboard_type) if instance.menu is not None else None

        return instance, effective_params, reply_markup

    def append_bot_message(self, record: BotMessageRecord) -> None:
        self._dialog.append_message(record)

    def _finalize(self, instance: BotMessageInstance, telegram_message: Message) -> BotMessageRecord:
        record = BotMessageRecord(
            type_name=instance.type_name,
            menu=instance.menu,
            data=instance.data,
            send_params=instance.send_params,
            telegram_message_instance=telegram_message,
        )
        if self._dialog.config.save_bot_message_nodes:
            self._dialog.append_message(record)
        return record

    async def _dispatch(
            self,
            prototype: BaseMessagePrototype,
            instance: BotMessageInstance,
            target: MessageTarget,
            effective_params: SendParams,
            reply_markup: Optional[InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply],
            context: Optional[dict[str, Any]] = None,
    ) -> BotMessageRecord:
        telegram_message = await prototype._do_send(self._bot, self, context, target, instance, effective_params, reply_markup)
        return self._finalize(instance, telegram_message)

    async def _send(
            self,
            prototype: BaseMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]],
            send_params: Optional[SendParams],
            keyboard_type: Optional[Literal["inline", "reply"]],
    ) -> BotMessageRecord:
        instance, effective_params, reply_markup = await self._prepare_instance(prototype, context, send_params, keyboard_type)
        return await self._dispatch(prototype, instance, target, effective_params, reply_markup, context)

    async def send_message(
            self,
            message_prototype: TextMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def reply_to_message(
            self,
            message_prototype: BaseMessagePrototype,
            reply_to: Message | AnyMessageRecord,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
            target: Optional[MessageTarget] = None,
    ) -> BotMessageRecord:
        if isinstance(reply_to, BaseMessageRecord):
            tg_message = reply_to.telegram_message_instance
        else:
            tg_message = reply_to

        instance, effective_params, reply_markup = await self._prepare_instance(
            message_prototype, context, send_params, keyboard_type
        )
        effective_params = effective_params.model_copy(
            update={"reply_parameters": ReplyParameters(message_id=tg_message.message_id)}
        )

        effective_target = target or MessageTarget.from_message(tg_message)
        return await self._dispatch(message_prototype, instance, effective_target, effective_params, reply_markup, context)

    async def edit_message(
            self,
            message_record: BotMessageRecord,
            message_prototype: TextMessagePrototype | BaseCaptionMediaPrototype,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
    ) -> BotMessageRecord:
        instance, effective_params, reply_markup = await self._prepare_instance(
            message_prototype, context, send_params, keyboard_type="inline"
        )
        tg = message_record.telegram_message_instance
        inline_markup = reply_markup if isinstance(reply_markup, InlineKeyboardMarkup) else None

        if isinstance(message_prototype, TextMessagePrototype):
            edit_params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _EDIT_COMPATIBLE_PARAMS}
            result = await self._bot.edit_message_text(
                chat_id=tg.chat.id,
                message_id=tg.message_id,
                text=instance.text,
                entities=instance.entities,
                reply_markup=inline_markup,
                business_connection_id=tg.business_connection_id,
                **edit_params,
            )
        else:
            edit_params = {k: v for k, v in effective_params.model_dump(exclude_unset=True).items() if k in _EDIT_CAPTION_PARAMS}
            result = await self._bot.edit_message_caption(
                chat_id=tg.chat.id,
                message_id=tg.message_id,
                caption=instance.text,
                caption_entities=instance.entities,
                reply_markup=inline_markup,
                business_connection_id=tg.business_connection_id,
                **edit_params,
            )

        if isinstance(result, Message):
            message_record.telegram_message_instance = result
        message_record.menu = instance.menu
        return message_record

    async def edit_message_media(
            self,
            message_record: BotMessageRecord,
            message_prototype: InputMediaPrototype,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
    ) -> BotMessageRecord:
        instance, effective_params, reply_markup = await self._prepare_instance(
            message_prototype, context, send_params, keyboard_type="inline"
        )
        tg = message_record.telegram_message_instance
        parse_mode = effective_params.model_dump(exclude_unset=True).get("parse_mode")
        media = await message_prototype.get_input_media(self, context, parse_mode)
        inline_markup = reply_markup if isinstance(reply_markup, InlineKeyboardMarkup) else None

        result = await self._bot.edit_message_media(
            chat_id=tg.chat.id,
            message_id=tg.message_id,
            media=media,
            reply_markup=inline_markup,
            business_connection_id=tg.business_connection_id,
        )
        if isinstance(result, Message):
            message_record.telegram_message_instance = result
        message_record.menu = instance.menu
        return message_record

    async def edit_live_location(
            self,
            message_record: BotMessageRecord,
            message_prototype: LocationMessagePrototype,
            context: Optional[dict[str, Any]] = None,
    ) -> BotMessageRecord:
        tg = message_record.telegram_message_instance
        latitude = await message_prototype.get_latitude(self, context)
        longitude = await message_prototype.get_longitude(self, context)
        extra = await message_prototype.get_extra_params(self, context)
        menu_instance = await message_prototype.get_menu(self, context)
        markup = menu_instance.get_markup("inline") if menu_instance is not None else None
        inline_markup = markup if isinstance(markup, InlineKeyboardMarkup) else None

        result = await self._bot.edit_message_live_location(
            chat_id=tg.chat.id,
            message_id=tg.message_id,
            latitude=latitude,
            longitude=longitude,
            business_connection_id=tg.business_connection_id,
            reply_markup=inline_markup,
            **extra.model_dump(exclude_none=True),
        )
        if isinstance(result, Message):
            message_record.telegram_message_instance = result
        return message_record

    async def edit_reply_markup(
            self,
            message_record: BotMessageRecord,
            menu_prototype: MenuPrototype,
            context: Optional[dict[str, Any]] = None,
    ) -> BotMessageRecord:
        tg = message_record.telegram_message_instance
        menu_instance = await menu_prototype.get_instance(self, context)
        markup = menu_instance.get_markup("inline")
        inline_markup = markup if isinstance(markup, InlineKeyboardMarkup) else None

        result = await self._bot.edit_message_reply_markup(
            chat_id=tg.chat.id,
            message_id=tg.message_id,
            business_connection_id=tg.business_connection_id,
            reply_markup=inline_markup,
        )
        if isinstance(result, Message):
            message_record.telegram_message_instance = result
        return message_record

    async def send_photo(
            self,
            message_prototype: PhotoMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_document(
            self,
            message_prototype: DocumentMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_video(
            self,
            message_prototype: VideoMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_audio(
            self,
            message_prototype: AudioMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_voice(
            self,
            message_prototype: VoiceMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_animation(
            self,
            message_prototype: AnimationMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_sticker(
            self,
            message_prototype: StickerMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_video_note(
            self,
            message_prototype: VideoNoteMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_location(
            self,
            message_prototype: LocationMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_contact(
            self,
            message_prototype: ContactMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_poll(
            self,
            message_prototype: PollMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
            keyboard_type: Optional[Literal["inline", "reply"]] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, keyboard_type)

    async def send_media_group(
            self,
            message_prototype: MediaGroupMessagePrototype,
            target: MessageTarget,
            context: Optional[dict[str, Any]] = None,
            send_params: Optional[SendParams] = None,
    ) -> BotMessageRecord:
        return await self._send(message_prototype, target, context, send_params, None)

    async def delete_message(self, message_record: BotMessageRecord) -> None:
        tg = message_record.telegram_message_instance
        await self._bot.delete_message(chat_id=tg.chat.id, message_id=tg.message_id)

    async def delete_all_messages(self, only_current_branch: bool = False) -> None:
        messages = (
            self._dialog.entries
            if only_current_branch
            else (node.message for node in self._dialog.nodes.values())
        )
        for message in messages:
            if isinstance(message, BotMessageRecord):
                tg = message.telegram_message_instance
                try:
                    await self._bot.delete_message(chat_id=tg.chat.id, message_id=tg.message_id)
                except TelegramBadRequest:
                    logger.debug("Message %s in chat %s already deleted or not found", tg.message_id, tg.chat.id)
                   