import json
from arena.i18n import locales

def write(root, code, meta, ui):
    d = root / code; d.mkdir(parents=True)
    (d / "locale.json").write_text(json.dumps({"code": code, **meta}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps(ui), encoding="utf-8")

def test_flatten_nested_keys():
    assert locales.flatten({"a": {"b": "x", "c": {"d": "y"}}}) == {"a.b": "x", "a.c.d": "y"}

def test_completeness_counts_non_empty_and_plural_groups_once(tmp_path):
    meta = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}
    write(tmp_path, "en", meta, {"a": "A", "n_one": "{{count}} item", "n_other": "{{count}} items", "b": "B"})
    write(tmp_path, "xx", meta, {"a": "AA", "n_one": "", "n_other": "{{count}} xs", "b": ""})
    assert locales.completeness("xx", root=tmp_path) == 2 / 3

def test_available_lists_en_first(tmp_path):
    meta = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}
    write(tmp_path, "hu", meta, {"a": "A"}); write(tmp_path, "en", meta, {"a": "A"})
    assert [x["code"] for x in locales.available(tmp_path)] == ["en", "hu"]
    assert locales.available(tmp_path)[1]["completeness"] == 1.0

def test_repo_locales_load():
    found = locales.discover()
    assert {"en", "hu"} <= set(found)
    assert found["hu"]["status"] == "beta"

META = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}

def test_malformed_catalog_does_not_break_available(tmp_path):
    write(tmp_path, "en", META, {"a": "A"}); write(tmp_path, "hu", META, {"a": "A"})
    (tmp_path / "hu" / "ui.json").write_text("{broken", encoding="utf-8")
    got = {x["code"]: x["completeness"] for x in locales.available(tmp_path)}
    assert got == {"en": 1.0, "hu": 0.0}

def test_non_object_catalog_is_zero_completeness(tmp_path):
    write(tmp_path, "en", META, {"a": "A"}); write(tmp_path, "hu", META, [1])
    assert locales.completeness("hu", root=tmp_path) == 0.0

def test_discover_skips_invalid_codes(tmp_path):
    write(tmp_path, "en", META, {}); write(tmp_path, "EN-us", META, {}); write(tmp_path, "hu_HU", META, {})
    assert set(locales.discover(tmp_path)) == {"en"}
