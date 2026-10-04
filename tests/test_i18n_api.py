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

def test_post_invalid_bodies_are_400(client):
    assert client.post("/api/i18n", json=["hu"]).status_code == 400
    assert client.post("/api/i18n", json={"language": 5}).status_code == 400
    r = client.post("/api/i18n", content="{nope", headers={"Content-Type": "application/json"})
    assert r.status_code == 400

def test_non_dict_settings_file_falls_back_and_is_overwritten(client):
    settings.SETTINGS.write_text("[1, 2]", encoding="utf-8")
    assert settings.get_language() == "en"
    assert settings.set_language("hu") == "hu"
    assert settings.get_language() == "hu"

def test_api_survives_broken_catalog(client, tmp_path, monkeypatch):
    import json
    from arena.i18n import locales
    meta = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}
    for code in ("en", "xx"):
        d = tmp_path / "loc" / code; d.mkdir(parents=True)
        (d / "locale.json").write_text(json.dumps({"code": code, **meta}), encoding="utf-8")
        (d / "ui.json").write_text('{"a": "A"}' if code == "en" else "{broken", encoding="utf-8")
    monkeypatch.setattr(locales, "LOCALES", tmp_path / "loc")
    r = client.get("/api/i18n")
    assert r.status_code == 200
    assert {x["code"]: x["completeness"] for x in r.json()["locales"]} == {"en": 1.0, "xx": 0.0}
