import json
from arena.i18n import check

META = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}

def write(root, code, ui, meta=None):
    d = root / code; d.mkdir(parents=True, exist_ok=True)
    (d / "locale.json").write_text(json.dumps({"code": code, **(META if meta is None else meta)}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps(ui), encoding="utf-8")

def levels(issues): return sorted((i.level, i.key) for i in issues)

def test_clean_locale_has_no_issues(tmp_path):
    write(tmp_path, "en", {"a": "Hi {{name}}"}); write(tmp_path, "xx", {"a": "Szia {{name}}"})
    assert check.check("xx", tmp_path) == []

def test_extra_key_and_placeholder_mismatch_are_errors(tmp_path):
    write(tmp_path, "en", {"a": "Hi {{name}}"}); write(tmp_path, "xx", {"a": "Szia {{nev}}", "z": "x"})
    assert levels(check.check("xx", tmp_path)) == [("error", "a"), ("error", "z")]

def test_missing_and_empty_are_warnings(tmp_path):
    write(tmp_path, "en", {"a": "A", "b": "B"}); write(tmp_path, "xx", {"a": ""})
    assert levels(check.check("xx", tmp_path)) == [("warning", "a"), ("warning", "b")]

def test_plural_group_needs_other(tmp_path):
    write(tmp_path, "en", {"n_one": "{{count}} x", "n_other": "{{count}} xs"})
    write(tmp_path, "xx", {"n_one": "{{count}} y"})
    assert ("error", "n") in levels(check.check("xx", tmp_path))

def test_bad_metadata_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"}); write(tmp_path, "xx", {"a": "A"}, meta={**META, "status": "done"})
    assert any(i.level == "error" and i.file == "locale.json" for i in check.check("xx", tmp_path))

def test_new_language_scaffold_is_valid_and_empty(tmp_path):
    write(tmp_path, "en", {"g": {"a": "A {{n}}"}})
    check.new_language("xx", "Example", "Exemplum", tmp_path)
    assert json.loads((tmp_path / "xx" / "ui.json").read_text(encoding="utf-8")) == {"g": {"a": ""}}
    assert json.loads((tmp_path / "xx" / "locale.json").read_text(encoding="utf-8"))["status"] == "beta"
    assert all(i.level == "warning" for i in check.check("xx", tmp_path))

def test_repo_locales_have_no_errors():
    assert [i for i in check.check() if i.level == "error"] == []
