import uuid
from typing import Optional, Literal

from aiogram.types import WebAppInfo, LoginUrl, SwitchInlineQueryChosenChat, CopyTextButton, CallbackGame, InlineKeyboardButton, KeyboardButton, KeyboardButtonRequestUsers, \
    KeyboardButtonRequestChat, KeyboardButtonPollType
from pydantic import BaseModel, Field


class ButtonAdditionalParameters(BaseModel):
    icon_custom_emoji_id: Optional[str] = Field(None, description="Custom emoji ID for the button icon")
    style: Optional[Literal["danger", "success", "primary"]] = Field(None, description="Style of the button")
    web_app: Optional[WebAppInfo] = Field(None, description="Description of the Web App that will be launched when the user presses the button")


class InlineButtonAdditionalParameters(ButtonAdditionalParameters):
    url: Optional[str] = Field(None, description="URL to be opened when the button is pressed")
    login_url: Optional[LoginUrl] = Field(None, description="An HTTPS URL used to automatically authorize the user, can be used as a replacement for the Telegram Login Widget")
    switch_inline_query: Optional[str] = Field(None, description="If set, pressing the button will prompt the user to select one of their chats, "
                                                                 "open that chat and insert the bot's username and the specified inline query in the input field")
    switch_inline_query_current_chat: Optional[str] = Field(None, description="If set, pressing the button will insert the bot's username "
                                                                              "and the specified inline query in the current chat's input field")
    switch_inline_query_chosen_chat: Optional[SwitchInlineQueryChosenChat] = Field(None, description="If set, pressing the button will prompt the user to select "
                                                                                                     "one of their chats of the specified type, open that chat and "
                                                                                                     "insert the bot's username and the specified inline query in the input field")
    copy_text: Optional[CopyTextButton] = Field(None, description="Description of the button that copies the specified text to the clipboard")
    callback_game: Optional[CallbackGame] = Field(None, description="Description of the game that will be launched when the user presses the button")
    pay: Optional[bool] = Field(None, description="Specify True to send a Pay button, substrings '⭐' and 'XTR' in the button's text will be replaced with a Telegram Star icon")


class CommonButtonAdditionalParameters(ButtonAdditionalParameters):
    request_users: Optional[KeyboardButtonRequestUsers] = Field(None, description="If specified, pressing the button will open a list of suitable users. "
                                                                                  "Identifiers of selected users will be sent to the bot in a 'users_shared' service message. "
                                                                                  "Available in private chats only.")
    request_chat: Optional[KeyboardButtonRequestChat] = Field(None, description="If specified, pressing the button will open a list of suitable chats. "
                                                                                "Tapping on a chat will send its identifier to the bot in a 'chat_shared' service message. "
                                                                                "Available in private chats only.")
    request_contact: Optional[bool] = Field(None, description="If True, the user's phone number will be sent as a contact when the button is pressed. "
                                                              "Available in private chats only.")
    request_location: Optional[bool] = Field(None, description="If True, the user's current location will be sent when the button is pressed. Available in private chats only.")
    request_poll: Optional[KeyboardButtonPollType] = Field(None, description="If specified and is not None, the user will be asked to create a poll "
                                                                             "and send it to the bot when the button is pressed. Available in private chats only.")


class ButtonInstance(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="Unique identifier for the button")
    text: str = Field(..., description="Text to be displayed on the button")
    type_name: str = Field(..., description="Type name of the button, used to identify which prototype it was created from")
    data: dict = Field(default_factory=dict, description="Additional data of the button")

    inline_additional_parameters: Optional[InlineButtonAdditionalParameters] = Field(None, description="Additional parameters for the inline button")
    common_additional_parameters: Optional[CommonButtonAdditionalParameters] = Field(None, description="Additional parameters for the common button")

    def get_inline_keyboard_button(self):
        additional_parameters = self.inline_additional_parameters.model_dump(exclude_unset=True, exclude_none=True) if self.inline_additional_parameters else {}
        return InlineKeyboardButton(
            text=self.text,
            callback_data=f"b:{self.id}",
            **additional_parameters
        )

    def get_common_keyboard_button(self):
        additional_parameters = self.common_additional_parameters.model_dump(exclude_unset=True, exclude_none=True) if self.common_additional_parameters else {}
        return KeyboardButton(
            text=self.text,
            **additional_parameters
        )
