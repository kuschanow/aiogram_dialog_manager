import uuid
from typing import Optional, Literal, Annotated, Union

from aiogram.client.default import Default
from aiogram.types import Message, LinkPreviewOptions, MessageEntity, ReplyParameters, SuggestedPostParameters, Chat
from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from aiogram_dialog_manager.instance.menu import AnyMenuInstance


class BaseMessageRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    data: dict = Field(default_factory=dict)
    telegram_message_instance: Message


class UserMessageRecord(BaseMessageRecord):
    is_bot_message: Literal[False] = Field(False, frozen=True)


class MessageTarget(BaseModel):
    chat_id: Union[int, str] = Field(..., description="Target chat identifier.")
    message_thread_id: Optional[int] = Field(None, description="Target forum topic thread ID.")
    business_connection_id: Optional[str] = Field(None, description="Business connection to send on behalf of.")
    direct_messages_topic_id: Optional[int] = Field(None, description="Target direct messages topic ID. Cannot be derived from a Message — must be provided manually.")

    @classmethod
    def from_message(cls, message: Message) -> "MessageTarget":
        return cls(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id if message.is_topic_message else None,
            business_connection_id=message.business_connection_id,
        )

    @classmethod
    def from_chat(cls, chat: Chat) -> "MessageTarget":
        return cls(chat_id=chat.id)


class SendParams(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    parse_mode: Optional[Union[str, Default]] = Field(Default("parse_mode"), description="Mode for parsing entities in the message text.")
    link_preview_options: Optional[Union[LinkPreviewOptions, Default]] = Field(Default("link_preview"), description="Link preview generation options.")
    disable_notification: Optional[bool] = Field(None, description="Sends the message silently.")
    protect_content: Optional[Union[bool, Default]] = Field(Default("protect_content"), description="Protects the contents of the sent message from forwarding and saving.")
    allow_paid_broadcast: Optional[bool] = Field(None, description="Allow up to 1000 messages per second, ignoring broadcasting limits for a fee.")
    message_effect_id: Optional[str] = Field(None, description="Unique identifier of the message effect to be added to the message.")
    suggested_post_parameters: Optional[SuggestedPostParameters] = Field(None, description="Parameters for a suggested post in a channel.")
    reply_parameters: Optional[ReplyParameters] = Field(None, description="Description of the message to reply to.")
    allow_sending_without_reply: Optional[bool] = Field(None, description="Send the message even if the replied-to message is not found.")
    disable_web_page_preview: Optional[Union[bool, Default]] = Field(Default("link_preview_is_disabled"),
                                                                     description="Disables link previews for links in this message. Deprecated, use link_preview_options instead.")

    @model_validator(mode="before")
    @classmethod
    def _restore_defaults(cls, data):
        if isinstance(data, dict):
            return {
                k: Default(v["__default__"]) if isinstance(v, dict) and "__default__" in v else v
                for k, v in data.items()
            }
        return data

    @model_serializer(mode="plain", when_used="json")
    def _serialize_defaults(self) -> dict:
        result = {}
        for field_name in self.__class__.model_fields:
            value = getattr(self, field_name)
            result[field_name] = {"__default__": value.name} if isinstance(value, Default) else value
        return result


class BotMessageInstance(BaseModel):
    type_name: str
    text: Optional[str] = None
    entities: Optional[list[MessageEntity]] = None
    menu: Optional[AnyMenuInstance] = None
    data: dict = Field(default_factory=dict)
    send_params: SendParams = Field(default_factory=SendParams)


class BotMessageRecord(BaseMessageRecord):
    is_bot_message: Literal[True] = Field(True, frozen=True)
    type_name: str
    menu: Optional[AnyMenuInstance] = None
    send_params: SendParams = Field(default_factory=SendParams)


AnyMessageRecord = Annotated[
    Union[UserMessageRecord, BotMessageRecord],
    Field(discriminator="is_bot_message")
]
