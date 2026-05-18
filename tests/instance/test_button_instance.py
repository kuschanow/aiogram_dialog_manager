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
