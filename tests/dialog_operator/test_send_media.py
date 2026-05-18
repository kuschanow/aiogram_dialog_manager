from aiogram_dialog_manager.instance.message import BotMessageRecord, MessageTarget
from tests.helpers import (
    StubAnimation, StubAudio, StubContact, StubDocument, StubLocation,
    StubMediaGroup, StubPhoto, StubPoll, StubSticker, StubVideo, StubVideoNote, StubVoice,
)


def make_target(chat_id=100) -> MessageTarget:
    return MessageTarget(chat_id=chat_id)


class TestSendMediaTypes:
    async def test_send_photo(self, operator, mock_bot):
        record = await operator.send_photo(StubPhoto(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_photo.assert_awaited_once()

    async def test_send_document(self, operator, mock_bot):
        record = await operator.send_document(StubDocument(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_document.assert_awaited_once()

    async def test_send_video(self, operator, mock_bot):
        record = await operator.send_video(StubVideo(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_video.assert_awaited_once()

    async def test_send_audio(self, operator, mock_bot):
        record = await operator.send_audio(StubAudio(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_audio.assert_awaited_once()

    async def test_send_animation(self, operator, mock_bot):
        record = await operator.send_animation(StubAnimation(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_animation.assert_awaited_once()

    async def test_send_voice(self, operator, mock_bot):
        record = await operator.send_voice(StubVoice(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_voice.assert_awaited_once()

    async def test_send_sticker(self, operator, mock_bot):
        record = await operator.send_sticker(StubSticker(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_sticker.assert_awaited_once()

    async def test_send_video_note(self, operator, mock_bot):
        record = await operator.send_video_note(StubVideoNote(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_video_note.assert_awaited_once()

    async def test_send_location(self, operator, mock_bot):
        record = await operator.send_location(StubLocation(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_location.assert_awaited_once()

    async def test_send_contact(self, operator, mock_bot):
        record = await operator.send_contact(StubContact(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_contact.assert_awaited_once()

    async def test_send_poll(self, operator, mock_bot):
        record = await operator.send_poll(StubPoll(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_poll.assert_awaited_once()

    async def test_send_media_group(self, operator, mock_bot):
        record = await operator.send_media_group(StubMediaGroup(), make_target())
        assert isinstance(record, BotMessageRecord)
        mock_bot.send_media_group.assert_awaited_once()
