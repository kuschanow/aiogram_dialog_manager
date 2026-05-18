import uuid
from abc import abstractmethod
from typing import Optional, Literal, Annotated, Union

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply, ReplyMarkupUnion
from pydantic import BaseModel, Field

from aiogram_dialog_manager.instance.button import ButtonInstance


class AdditionalReplyMenuParameters(BaseModel):
    is_persistent: bool = Field(default=False, description="Requests clients to always show the keyboard when the regular keyboard is hidden. "
                                                           "The user can hide the keyboard using a special button in the input field, "
                                                           "and the keyboard will automatically be shown again when the user starts typing in the input field.")
    resize_keyboard: bool = Field(default=False, description="Requests clients to resize the keyboard vertically for optimal fit "
                                                             "(e.g., make the keyboard smaller if there are just two rows of buttons).")
    one_time_keyboard: bool = Field(default=False, description="Requests clients to hide the keyboard as soon as it's been used. The keyboard will still be available, "
                                                               "but clients will automatically display the usual letter-keyboard in the chat – the user can press a special button "
                                                               "in the input field to see the custom keyboard again.")
    input_field_placeholder: str = Field(default="", description="The placeholder to be shown in the input field when the keyboard is active; 1-64 characters")
    selective: bool = Field(default=False, description="Use this parameter if you want to show the keyboard to specific users only. Targets: "
                                                       "1) users that are @mentioned in the text of the Message object; "
                                                       "2) if the bot's message is a reply (has reply_to_message_id), sender of the original message.")


class BaseMenuInstance(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="A unique identifier for the menu instance.")
    type_name: str = Field(..., description="The type name of the menu, used to identify which prototype it was created from.")
    data: dict = Field(default_factory=dict, description="Additional data for the menu, can be used for dynamic content or state management.")

    @abstractmethod
    def get_markup(self, keyboard_type: Optional[Literal["inline", "reply"]] = None) -> ReplyMarkupUnion:
        pass


class MenuInstance(BaseMenuInstance):
    menu_type: Literal["buttons"] = Field("buttons", frozen=True)

    buttons: list[list[ButtonInstance]] = Field(..., min_length=1, description="A 2D list of buttons, where each inner list represents a row of buttons.")
    keyboard_type: Literal["inline", "reply"] = Field("inline", description="Whether to render as an inline keyboard or a reply keyboard.")
    additional_reply_parameters: Optional[AdditionalReplyMenuParameters] = Field(None,
                                                                                 description="Additional parameters for reply keyboards. Only used when keyboard_type is 'reply'.")

    def get_markup(self, keyboard_type: Optional[Literal["inline", "reply"]] = None) -> Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]:
        effective_type = keyboard_type or self.keyboard_type
        if effective_type == "inline":
            return InlineKeyboardMarkup(inline_keyboard=[
                [button.get_inline_keyboard_button() for button in row]
                for row in self.buttons
            ])

        additional = self.additional_reply_parameters.model_dump(exclude_unset=True, exclude_none=True) if self.additional_reply_parameters else {}
        return ReplyKeyboardMarkup(keyboard=[
            [button.get_common_keyboard_button() for button in row]
            for row in self.buttons
        ], **additional)


class ForceReplyMenuInstance(BaseMenuInstance):
    menu_type: Literal["force_reply"] = Field("force_reply", frozen=True)

    input_field_placeholder: Optional[str] = Field(None, description="The placeholder to be shown in the input field when reply is active; 1-64 characters.")
    selective: Optional[bool] = Field(None, description="Use this parameter if you want to force reply from specific users only.")

    def get_markup(self, keyboard_type: Optional[Literal["inline", "reply"]] = None) -> ForceReply:
        return ForceReply(
            force_reply=True,
            input_field_placeholder=self.input_field_placeholder,
            selective=self.selective,
        )


class RemoveKeyboardMenuInstance(BaseMenuInstance):
    menu_type: Literal["remove_keyboard"] = Field("remove_keyboard", frozen=True)

    selective: Optional[bool] = Field(None, description="Use this parameter if you want to remove the keyboard for specific users only.")

    def get_markup(self, keyboard_type: Optional[Literal["inline", "reply"]] = None) -> ReplyKeyboardRemove:
        return ReplyKeyboardRemove(remove_keyboard=True, selective=self.selective)


AnyMenuInstance = Annotated[
    Union[MenuInstance, ForceReplyMenuInstance, RemoveKeyboardMenuInstance],
    Field(discriminator="menu_type")
]
