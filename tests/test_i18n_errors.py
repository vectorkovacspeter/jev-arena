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
