from aiogram_dialog_manager.instance.button import (
    ButtonInstance,
    CommonButtonAdditionalParameters,
    InlineButtonAdditionalParameters,
)


class TestButtonInstance:
    def test_get_inline_keyboard_button_basic(self):
        btn = ButtonInstance(text="Press", type_name="my_btn")
        kb_btn = btn.get_inline_keyboard_button()
        assert kb_btn.text == "Press"
        assert kb_btn.callback_data == f"b:{btn.id}"

    def test_get_inline_keyboard_button_with_extra(self):
        extra = InlineButtonAdditionalParameters(url="https://example.com")
        btn = ButtonInstance(text="Link", type_name="link_btn", inline_additional_parameters=extra)
        kb_btn = btn.get_inline_keyboard_button()
        assert kb_btn.url == "https://example.com"

    def test_get_common_keyboard_button_basic(self):
        btn = ButtonInstance(text="Reply", type_name="reply_btn")
        kb_btn = btn.get_common_keyboard_button()
        assert kb_btn.text == "Reply"

    def test_get_common_keyboard_button_with_extra(self):
        extra = CommonButtonAdditionalParameters(request_contact=True)
        btn = ButtonInstance(text="Share", type_name="share_btn", common_additional_parameters=extra)
        kb_btn = btn.get_common_keyboard_button()
        assert kb_btn.request_contact is True

    def test_button_has_unique_id(self):
        b1 = ButtonInstance(text="A", type_name="t")
        b2 = ButtonInstance(text="B", type_name="t")
        assert b1.id != b2.id


class TestButtonSerialization:
    def test_button_additional_parameters_roundtrip(self):
        from aiogram_dialog_manager.instance.button import ButtonAdditionalParameters
        params = ButtonAdditionalParameters(style="primary")
        dumped = params.model_dump(mode="json")
        restored = ButtonAdditionalParameters.model_validate(dumped)
        assert restored.style == "primary"
        assert restored.icon_custom_emoji_id is None

    def test_inline_additional_parameters_roundtrip(self):
        extra = InlineButtonAdditionalParameters(url="https://example.com", pay=True)
        dumped = extra.model_dump(mode="json")
        restored = InlineButtonAdditionalParameters.model_validate(dumped)
        assert restored.url == "https://example.com"
        assert restored.pay is True

    def test_common_additional_parameters_roundtrip(self):
        extra = CommonButtonAdditionalParameters(request_contact=True, request_location=False)
        dumped = extra.model_dump(mode="json")
        restored = CommonButtonAdditionalParameters.model_validate(dumped)
        assert restored.request_contact is True
        assert restored.request_location is False

    def test_button_instance_roundtrip(self):
        btn = ButtonInstance(text="Click", type_name="my_btn", data={"k": "v"})
        dumped = btn.model_dump(mode="json")
        restored = ButtonInstance.model_validate(dumped)
        assert restored.id == btn.id
        assert restored.text == "Click"
        assert restored.type_name == "my_btn"
        assert restored.data == {"k": "v"}

    def test_button_instance_with_inline_params_roundtrip(self):
        extra = InlineButtonAdditionalParameters(url="https://t.me")
        btn = ButtonInstance(text="Link", type_name="link", inline_additional_parameters=extra)
        dumped = btn.model_dump(mode="json")
        restored = ButtonInstance.model_validate(dumped)
        assert restored.inline_additional_parameters.url == "https://t.me"
