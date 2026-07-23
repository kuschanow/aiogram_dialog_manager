"""Tests for translation extraction from spec models."""
import io
import json

from aiogram_dialog_manager.spec import DialogSpec, extract_spec, iter_translation_keys


def make_spec() -> DialogSpec:
    return DialogSpec.from_dict({
        "name": "dlg",
        "windows": {
            "main": {
                "content": {"type": "text", "text": [{"type": "t", "key": "welcome"}, "!"]},
                "menu": {"rows": [[{"type": "button", "name": "save", "text": {"type": "t", "key": "save_btn"}}]]},
            },
        },
        "defs": {"footer": {"type": "t", "key": "footer_text"}},
    })


class TestIterTranslationKeys:
    def test_model_yields_every_msgid(self):
        assert sorted(iter_translation_keys(make_spec())) == ["footer_text", "save_btn", "welcome"]

    def test_dict_form_yields_every_msgid(self):
        assert sorted(iter_translation_keys(make_spec().to_dict())) == ["footer_text", "save_btn", "welcome"]

    def test_duplicates_preserved(self):
        payload = [{"type": "t", "key": "dup"}, {"nested": {"type": "t", "key": "dup"}}]
        assert list(iter_translation_keys(payload)) == ["dup", "dup"]

    def test_malformed_t_nodes_skipped(self):
        payload = {"type": "t", "key": 42}
        assert list(iter_translation_keys(payload)) == []

    def test_scalars_ignored(self):
        assert list(iter_translation_keys("just a string")) == []


class TestExtractSpec:
    def extract(self, source: str, options=None):
        return list(extract_spec(io.BytesIO(source.encode()), None, None, options))

    def test_extracts_messages_with_line_numbers(self):
        source = json.dumps(make_spec().to_dict(), indent=1)
        results = self.extract(source)
        assert {message for _, _, message, _ in results} == {"welcome", "save_btn", "footer_text"}
        lines = source.splitlines()
        for lineno, funcname, message, comments in results:
            assert funcname is None
            assert comments == []
            assert json.dumps(message) in lines[lineno - 1]

    def test_minified_source_falls_back_to_line_one(self):
        source = json.dumps({"type": "t", "key": "hello"})
        assert self.extract(source) == [(1, None, "hello", [])]

    def test_repeated_msgids_advance_lines(self):
        source = json.dumps([{"type": "t", "key": "dup"}, {"type": "t", "key": "dup"}], indent=1)
        linenos = [lineno for lineno, _, _, _ in self.extract(source)]
        assert len(linenos) == 2
        assert linenos[0] < linenos[1]

    def test_second_occurrence_beyond_source_falls_back(self):
        # Two msgids in the model but the literal occurs once in the source
        # (e.g. hand-minified duplicates) — the second yield falls back to 1.
        source = '[{"type": "t", "key": "dup"}, {"type": "t", "key": "dup"}]'
        assert [lineno for lineno, _, _, _ in self.extract(source)] == [1, 1]

    def test_non_ascii_msgid(self):
        source = json.dumps({"type": "t", "key": "привет"}, ensure_ascii=False, indent=1)
        results = self.extract(source)
        assert results == [(3, None, "привет", [])]

    def test_ascii_escaped_msgid_found(self):
        source = json.dumps({"type": "t", "key": "привет"}, ensure_ascii=True, indent=1)
        assert self.extract(source) == [(3, None, "привет", [])]

    def test_custom_encoding_option(self):
        payload = json.dumps({"type": "t", "key": "café"}, ensure_ascii=False)
        results = list(extract_spec(io.BytesIO(payload.encode("latin-1")), None, None, {"encoding": "latin-1"}))
        assert results == [(1, None, "café", [])]
