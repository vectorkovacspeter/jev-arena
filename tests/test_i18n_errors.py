import pytest
from fastapi.testclient import TestClient
from arena.i18n.errors import ArenaError
from arena import suites

def test_arena_error_is_value_error_with_original_text():
    e = ArenaError("setup_needed", "Setup needed: x", details="x")
    assert isinstance(e, ValueError) and str(e) == "Setup needed: x"
    assert e.code == "setup_needed" and e.params == {"details": "x"}

def test_suite_error_keeps_english_and_adds_code(monkeypatch):
    monkeypatch.setattr(suites, "jevbench", lambda: [])
    with pytest.raises(ArenaError) as info: suites.suite("demo")
    assert info.value.code == "demo_needs_sources"
    assert str(info.value) == "Demo needs the pinned public JevBench sources. Use Prepare selected in Setup first."

def test_http_error_body_has_code():
    from arena.api import app
    r = TestClient(app).get("/api/runs/unknown")
    assert r.status_code == 404
    assert r.json() == {"detail": "Run not found", "code": "run_not_found", "params": {}}

def test_every_code_has_english_catalog_entry():
    import re
    from arena.config import ROOT
    from arena.i18n.locales import flatten, load_catalog
    keys = flatten(load_catalog("en"))
    source = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "arena").rglob("*.py"))
    codes = set(re.findall(r"""Arena(?:HTTP)?Error\((?:\d+,\s*)?['"]([a-z_]+)['"]""", source))
    assert codes and all(f"errors.{c}" in keys for c in codes)


def _en():
    from arena.i18n.locales import flatten, load_catalog
    return flatten(load_catalog("en"))

def test_reasons_match_readiness_catalog():
    from arena.controller import REASONS
    keys = _en()
    assert REASONS and all(keys[f"readiness.{c}"] == text for c, text in REASONS.items())

def test_reason_code_for_covers_each_branch():
    from arena.controller import reason_code_for, REASONS
    from arena.adapters import IMPLEMENTED
    impl = next(iter(IMPLEMENTED))
    assert reason_code_for({"hosted": True, "runtime": impl}, None, True) is None
    assert reason_code_for({"hosted": True, "runtime": impl}, None, False) == "add_typesafe_key"
    assert reason_code_for({"hosted": False, "runtime": "nope"}, None, False) == "native_pending"
    assert reason_code_for({"hosted": False, "runtime": impl}, None, False) == "prepare_weights"
    assert reason_code_for({"hosted": False, "runtime": impl}, {"x": 1}, False) == "gpu_unavailable"
    assert all(c in REASONS for c in ("add_typesafe_key", "native_pending", "prepare_weights", "gpu_unavailable"))

def test_readiness_entries_have_reason_code():
    import asyncio
    from arena.api import controller
    r = asyncio.run(controller.readiness())
    assert r["models"] and all("reason_code" in m for m in r["models"])
    assert all((m["reason_code"] is None) == m["ready"] for m in r["models"])

def test_api_409_carries_code_and_params():
    from arena.api import app
    c = TestClient(app)
    token = c.get("/api/session").json()["token"]
    r = c.post("/api/runs", headers={"x-arena-token": token},
               json={"model_ids": ["uniform", "uniform"], "preset": "smoke", "idempotency_key": "dup-test-key-1"})
    assert r.status_code == 409, r.text
    assert r.json() == {"detail": "Duplicate entrants", "code": "duplicate_entrants", "params": {}}

def test_setup_needed_carries_models_and_json_serializable():
    import json
    from arena.controller import setup_needed_error
    e = setup_needed_error([{"name": "Laya", "reason": "Add your TypeSafe key", "reason_code": "add_typesafe_key"}])
    assert str(e) == "Setup needed: Laya: Add your TypeSafe key"
    assert e.params["details"] == "Laya: Add your TypeSafe key"
    assert e.params["models"] == [{"name": "Laya", "reason_code": "add_typesafe_key"}]
    json.dumps(e.params)

def test_suite_not_prepared_carries_packs(monkeypatch):
    import json
    monkeypatch.setattr(suites, "jevbench", lambda: [])
    monkeypatch.setattr(suites, "imported", lambda: [])
    monkeypatch.setattr(suites, "fresh", lambda: [])
    monkeypatch.setattr(suites, "robustness", lambda: [])
    with pytest.raises(ArenaError) as info: suites.suite("full")
    p = info.value.params
    assert info.value.code == "suite_not_prepared" and isinstance(p["packs"], dict)
    assert p["packs"]["JevBench public"] == {"expected": 231, "available": 0}
    assert p["missing"] == json.dumps(p["packs"])

def test_paramless_messages_match_catalog():
    import re
    from arena.config import ROOT
    keys = _en()
    source = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "arena").rglob("*.py"))
    pairs = re.findall(r"""Arena(?:HTTP)?Error\((?:\d+,\s*)?(['"])([a-z_]+)\1,\s*(['"])([^'"{}]*?)\3\)""", source)
    assert len(pairs) >= 15
    for _, code, _, msg in pairs:
        assert keys[f"errors.{code}"] == msg, code
