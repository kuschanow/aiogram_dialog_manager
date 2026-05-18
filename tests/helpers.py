"""Concrete implementations of abstract prototypes for use in tests."""

from aiogram.types import InputMediaPhoto

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.dialog import DialogConfig
from aiogram_dialog_manager.prototype.base import TextContent
from aiogram_dialog_manager.prototype.button import ButtonPrototype
from aiogram_dialog_manager.prototype.dialog import DialogPrototype
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


class StubButton(ButtonPrototype):
    def __init__(self, name="btn", state="Click"):
        self._name = name
        self._state = state

    @property
    def name(self) -> str:
        return self._name

    async def get_state(self, dialog, context) -> str:
        return self._state


class StubMenu(MenuPrototype):
    def __init__(self, name="menu", buttons=None):
        self._name = name
        self._buttons = buttons

    @property
    def name(self) -> str:
        return self._name

    async def get_buttons(self, dialog, context) -> list[list[ButtonInstance]]:
        if self._buttons is not None:
            return self._buttons
        btn = ButtonInstance(text="OK", type_name="btn")
        return [[btn]]


class StubDialog(DialogPrototype):
    def __init__(self, name="dialog", save_bot=True, save_user=True):
        self._name = name
        self._save_bot = save_bot
        self._save_user = save_user

    @property
    def name(self) -> str:
        return self._name

    async def get_config(self) -> DialogConfig:
        return DialogConfig(save_bot_message_nodes=self._save_bot, save_user_message_nodes=self._save_user)


class StubText(TextMessagePrototype):
    def __init__(self, text="Hello"):
        self._text = text

    @property
    def name(self) -> str:
        return "text_msg"

    async def get_text_content(self, dialog, context) -> TextContent:
        return TextContent(text=self._text)


class StubPhoto(PhotoMessagePrototype):
    @property
    def name(self) -> str:
        return "photo_msg"

    async def get_photo(self, dialog, context) -> str:
        return "photo_file_id"

    async def get_text_content(self, dialog, context) -> TextContent:
        return TextContent(text="caption")


class StubDocument(DocumentMessagePrototype):
    @property
    def name(self) -> str:
        return "doc_msg"

    async def get_document(self, dialog, context) -> str:
        return "doc_file_id"

    async def get_text_content(self, dialog, context) -> TextContent:
        return TextContent(text="caption")


class StubVideo(VideoMessagePrototype):
    @property
    def name(self) -> str:
        return "video_msg"

    async def get_video(self, dialog, context) -> str:
        return "video_file_id"

    async def get_text_content(self, dialog, context) -> TextContent:
        return TextContent(text="caption")


class StubAudio(AudioMessagePrototype):
    @property
    def name(self) -> str:
        return "audio_msg"

    async def get_audio(self, dialog, context) -> str:
        return "audio_file_id"

    async def get_text_content(self, dialog, context) -> TextContent:
        return TextContent(text="caption")


class StubAnimation(AnimationMessagePrototype):
    @property
    def name(self) -> str:
        return "anim_msg"

    async def get_animation(self, dialog, context) -> str:
        return "anim_file_id"

    async def get_text_content(self, dialog, context) -> TextContent:
        return TextContent(text="caption")


class StubVoice(VoiceMessagePrototype):
    @property
    def name(self) -> str:
        return "voice_msg"

    async def get_voice(self, dialog, context) -> str:
        return "voice_file_id"

    async def get_text_content(self, dialog, context) -> TextContent:
        return TextContent(text="caption")


class StubVoiceDefaultText(VoiceMessagePrototype):
    """VoiceMessagePrototype without get_text_content override — uses BaseCaptionMediaPrototype default."""

    @property
    def name(self) -> str:
        return "voice_default_text"

    async def get_voice(self, dialog, context) -> str:
        return "voice_file_id"


class StubSticker(StickerMessagePrototype):
    @property
    def name(self) -> str:
        return "sticker_msg"

    async def get_sticker(self, dialog, context) -> str:
        return "sticker_file_id"


class StubVideoNote(VideoNoteMessagePrototype):
    @property
    def name(self) -> str:
        return "video_note_msg"

    async def get_video_note(self, dialog, context) -> str:
        return "video_note_file_id"


class StubLocation(LocationMessagePrototype):
    @property
    def name(self) -> str:
        return "location_msg"

    async def get_latitude(self, dialog, context) -> float:
        return 55.75

    async def get_longitude(self, dialog, context) -> float:
        return 37.62


class StubContact(ContactMessagePrototype):
    @property
    def name(self) -> str:
        return "contact_msg"

    async def get_phone_number(self, dialog, context) -> str:
        return "+79001234567"

    async def get_first_name(self, dialog, context) -> str:
        return "John"


class StubPoll(PollMessagePrototype):
    @property
    def name(self) -> str:
        return "poll_msg"

    async def get_question(self, dialog, context) -> str:
        return "Best color?"

    async def get_options(self, dialog, context) -> list:
        return ["Red", "Blue"]


class StubMediaGroup(MediaGroupMessagePrototype):
    @property
    def name(self) -> str:
        return "media_group_msg"

    async def get_media(self, dialog, context) -> list:
        return [InputMediaPhoto(media="photo1"), InputMediaPhoto(media="photo2")]
