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
