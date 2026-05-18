from aiogram_dialog_manager.prototype.base import TextContent
from tests.helpers import StubPhoto, StubVoiceDefaultText


class TestBaseCaptionMediaPrototype:
    async def test_get_instance_builds_correctly(self, operator):
        proto = StubPhoto()
        instance = await proto.get_instance(operator, None)
        assert instance.type_name == "photo_msg"
        assert instance.text == "caption"

    async def test_get_text_content_default_returns_empty_text_content(self, operator):
        proto = StubVoiceDefaultText()
        text = await proto.get_text_content(operator, None)
        assert isinstance(text, TextContent)
        assert text.text is None
