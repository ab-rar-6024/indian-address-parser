import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from india_address_parser import FIELDS  # noqa: E402
from india_address_parser.server import MAX_BATCH, create_app  # noqa: E402


class FakeParser:
    def __init__(self):
        self.calls = []

    def parse(self, address):
        self.calls.append(address)
        if "boom" in address:
            raise ValueError("model did not return valid JSON: 'x'")
        return {k: (address.upper() if k == "street" else "") for k in FIELDS}


def client(api_key=None):
    parser = FakeParser()
    return TestClient(create_app(parser, api_key)), parser


def test_health_is_open_even_with_a_key():
    c, _ = client("secret")
    r = c.get("/health")
    assert r.status_code == 200 and r.json()["fields"] == FIELDS


def test_parse_returns_the_nine_fields():
    c, p = client()
    r = c.post("/parse", json={"address": "12 Mettu Street"})
    assert r.status_code == 200
    assert list(r.json()) == FIELDS and r.json()["street"] == "12 METTU STREET"
    assert p.calls == ["12 Mettu Street"]


@pytest.mark.parametrize("body", [{}, {"address": ""}, {"address": "x" * 501}, {"addresses": ["a"]}])
def test_parse_rejects_bad_input(body):
    c, _ = client()
    assert c.post("/parse", json=body).status_code == 422


def test_blank_address_is_422_not_a_model_call():
    c, p = client()
    assert c.post("/parse", json={"address": "   "}).status_code == 422
    assert p.calls == []


def test_model_failure_is_422_with_message():
    c, _ = client()
    r = c.post("/parse", json={"address": "boom"})
    assert r.status_code == 422 and "valid JSON" in r.json()["detail"]


def test_batch_keeps_order_and_isolates_failures():
    c, _ = client()
    r = c.post("/parse_batch", json={"addresses": ["a", "boom", "b"]})
    res = r.json()["results"]
    assert r.status_code == 200 and len(res) == 3
    assert res[0]["street"] == "A" and "error" in res[1] and res[2]["street"] == "B"


def test_batch_size_limit():
    c, _ = client()
    assert c.post("/parse_batch", json={"addresses": ["a"] * (MAX_BATCH + 1)}).status_code == 422
    assert c.post("/parse_batch", json={"addresses": []}).status_code == 422


def test_api_key_required_on_parse_endpoints():
    c, p = client("secret")
    for path, body in [("/parse", {"address": "a"}), ("/parse_batch", {"addresses": ["a"]})]:
        assert c.post(path, json=body).status_code == 401
        assert c.post(path, json=body, headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert c.post(path, json=body, headers={"Authorization": "secret"}).status_code == 401
        assert c.post(path, json=body, headers={"Authorization": "Bearer secret"}).status_code == 200
    assert len(p.calls) == 2  # only the two authorised calls reached the model
