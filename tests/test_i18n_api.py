import pytest
from fastapi.testclient import TestClient
from arena.i18n import settings

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SETTINGS", tmp_path / "settings.json")
    from arena.api import app
    c = TestClient(app)
    c.headers["X-Arena-Token"] = c.get("/api/session").json()["token"]
    return c

def test_default_language_is_english(client):
    body = client.get("/api/i18n").json()
    assert body["language"] == "en"
    assert {"en", "hu"} <= {x["code"] for x in body["locales"]}

def test_set_language_persists(client):
    assert client.post("/api/i18n", json={"language": "hu"}).json()["language"] == "hu"
    assert client.get("/api/i18n").json()["language"] == "hu"
    assert settings.get_language() == "hu"

def test_unknown_language_rejected(client):
    r = client.post("/api/i18n", json={"language": "xx"})
    assert r.status_code == 400
    assert client.get("/api/i18n").json()["language"] == "en"

def test_set_language_requires_token(client):
    del client.headers["X-Arena-Token"]
    assert client.post("/api/i18n", json={"language": "hu"}).status_code == 403

def test_corrupt_settings_fall_back(client):
    settings.SETTINGS.write_text("{not json", encoding="utf-8")
    assert settings.get_language() == "en"
