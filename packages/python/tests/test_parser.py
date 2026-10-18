import json
import sys
import types

import pytest


class FakeLlama:
    reply = json.dumps({"flat": "14/2", "street": "Gandhi Road", "area": "Pollachi", "city": "Coimbatore",
                        "state": "Tamil Nadu", "pincode": "642001", "extra": "dropped", "phone": None})
    last_kwargs = None

    def __init__(self, **kwargs):
        FakeLlama.last_kwargs = kwargs

    @classmethod
    def from_pretrained(cls, repo_id, filename, **kwargs):
        inst = cls()
        cls.last_kwargs = {"repo_id": repo_id, "filename": filename, **kwargs}
        return inst

    def create_chat_completion(self, messages, temperature, max_tokens):
        FakeLlama.messages = messages
        return {"choices": [{"message": {"content": FakeLlama.reply}}]}


@pytest.fixture(autouse=True)
def fake_llama(monkeypatch):
    mod = types.ModuleType("llama_cpp")
    mod.Llama = FakeLlama
    monkeypatch.setitem(sys.modules, "llama_cpp", mod)


def test_parse_returns_exactly_nine_string_fields():
    from india_address_parser import FIELDS, AddressParser
    out = AddressParser(model_path="x.gguf").parse("D.No 14/2, Gandhi Road, Pollachi, Coimbatore - 642001")
    assert list(out) == FIELDS
    assert out["flat"] == "14/2" and out["city"] == "Coimbatore" and out["phone"] == "" and out["building"] == ""
    assert "extra" not in out


def test_uses_training_system_prompt():
    from india_address_parser import SYSTEM, AddressParser
    AddressParser(model_path="x.gguf").parse("  anything  ")
    assert FakeLlama.messages[0] == {"role": "system", "content": SYSTEM}
    assert FakeLlama.messages[1]["content"] == "anything"


def test_default_downloads_q4_k_m_from_hub():
    from india_address_parser import AddressParser
    AddressParser()
    assert FakeLlama.last_kwargs["repo_id"] == "abr-6024/indian-address-parser-1.5B-GGUF"
    assert FakeLlama.last_kwargs["filename"] == "*Q4_K_M.gguf"


def test_invalid_model_output_raises():
    from india_address_parser import AddressParser
    FakeLlama.reply = "not json"
    with pytest.raises(ValueError):
        AddressParser(model_path="x.gguf").parse("addr")
    FakeLlama.reply = "[1, 2]"
    with pytest.raises(ValueError):
        AddressParser(model_path="x.gguf").parse("addr")


def test_empty_address_raises():
    from india_address_parser import AddressParser
    with pytest.raises(ValueError):
        AddressParser(model_path="x.gguf").parse("   ")
