from aiogram.client.default import Default
from aiogram.types import LinkPreviewOptions

from aiogram_dialog_manager.instance.message import SendParams


class TestSendParams:
    def test_default_fields_excluded_from_json(self):
        params = SendParams()
        dumped = params.model_dump(mode="json")
        assert "parse_mode" not in dumped
        assert "link_preview_options" not in dumped
        assert "protect_content" not in dumped

    def test_default_fields_restored_after_roundtrip(self):
        params = SendParams()
        dumped = params.model_dump(mode="json")
        restored = SendParams.model_validate(dumped)
        assert isinstance(restored.parse_mode, Default)
        assert isinstance(restored.link_preview_options, Default)
        assert isinstance(restored.protect_content, Default)

    def test_explicit_str_value_included_in_json(self):
        params = SendParams(parse_mode="HTML")
        dumped = params.model_dump(mode="json")
        assert dumped["parse_mode"] == "HTML"

    def test_explicit_bool_value_included_in_json(self):
        params = SendParams(protect_content=True)
        dumped = params.model_dump(mode="json")
        assert dumped["protect_content"] is True

    def test_explicit_none_included_in_json(self):
        params = SendParams(parse_mode=None)
        dumped = params.model_dump(mode="json")
        assert "parse_mode" in dumped
        assert dumped["parse_mode"] is None

    def test_link_preview_options_object_serialized_without_defaults(self):
        lpo = LinkPreviewOptions(is_disabled=True)
        params = SendParams(link_preview_options=lpo)
        dumped = params.model_dump(mode="json")
        assert isinstance(dumped["link_preview_options"], dict)
        assert dumped["link_preview_options"]["is_disabled"] is True
        assert "prefer_small_media" not in dumped["link_preview_options"]

    def test_none_link_preview_options_included_in_json(self):
        params = SendParams(link_preview_options=None)
        dumped = params.model_dump(mode="json")
        assert "link_preview_options" in dumped
        assert dumped["link_preview_options"] is None

    def test_link_preview_options_roundtrip(self):
        lpo = LinkPreviewOptions(is_disabled=True)
        params = SendParams(link_preview_options=lpo)
        dumped = params.model_dump(mode="json")
        restored = SendParams.model_validate(dumped)
        assert isinstance(restored.link_preview_options, LinkPreviewOptions)
        assert restored.link_preview_options.is_disabled is True

    def test_mixed_values_roundtrip(self):
        params = SendParams(
            parse_mode="MarkdownV2",
            link_preview_options=None,
            disable_notification=True,
            protect_content=None,
        )
        dumped = params.model_dump(mode="json")
        restored = SendParams.model_validate(dumped)
        assert restored.parse_mode == "MarkdownV2"
        assert restored.link_preview_options is None
        assert restored.disable_notification is True
        assert restored.protect_content is None

    def test_python_mode_preserves_defaults(self):
        params = SendParams()
        dumped = params.model_dump()
        assert isinstance(dumped["parse_mode"], Default)
        assert isinstance(dumped["protect_content"], Default)
