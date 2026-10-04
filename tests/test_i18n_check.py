import json
import re
import pytest
from arena.i18n import check
from arena.i18n.check import Issue
from arena.i18n.__main__ import main
from arena.i18n.locales import discover

META = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}

def write(root, code, ui, meta=None):
    d = root / code; d.mkdir(parents=True, exist_ok=True)
    (d / "locale.json").write_text(json.dumps({"code": code, **(META if meta is None else meta)}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps(ui), encoding="utf-8")

def test_clean_locale_has_no_issues(tmp_path):
    write(tmp_path, "en", {"a": "Hi {{name}}"})
    write(tmp_path, "xx", {"a": "Szia {{name}}"})
    assert check.check("xx", tmp_path) == []

def test_extra_key_and_placeholder_mismatch_are_errors(tmp_path):
    write(tmp_path, "en", {"a": "Hi {{name}}"})
    write(tmp_path, "xx", {"a": "Szia {{nev}}", "z": "x"})
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "ui.json", "a", "placeholders ['nev'] != en ['name']"),
        Issue("error", "xx", "ui.json", "z", "key not in en"),
    ]

def test_missing_and_empty_are_warnings(tmp_path):
    write(tmp_path, "en", {"a": "A", "b": "B"})
    write(tmp_path, "xx", {"a": ""})
    assert check.check("xx", tmp_path) == [
        Issue("warning", "xx", "ui.json", "a", "missing (falls back to en)"),
        Issue("warning", "xx", "ui.json", "b", "missing (falls back to en)"),
    ]

def test_plural_group_needs_other(tmp_path):
    write(tmp_path, "en", {"n_one": "{{count}} x", "n_other": "{{count}} xs"})
    write(tmp_path, "xx", {"n_one": "{{count}} y"})
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "ui.json", "n", "plural group needs an _other form"),
        Issue("warning", "xx", "ui.json", "n_other", "missing (falls back to en)"),
    ]

def test_bad_metadata_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "A"}, meta={**META, "status": "done"})
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "locale.json", "status", "must be complete or beta"),
    ]

def test_new_language_scaffold_is_valid_and_empty(tmp_path):
    write(tmp_path, "en", {"g": {"a": "A {{n}}"}})
    check.new_language("xx", "Example", "Exemplum", tmp_path)
    assert json.loads((tmp_path / "xx" / "ui.json").read_text(encoding="utf-8")) == {"g": {"a": ""}}
    assert json.loads((tmp_path / "xx" / "locale.json").read_text(encoding="utf-8"))["status"] == "beta"
    assert check.check("xx", tmp_path) == [
        Issue("warning", "xx", "ui.json", "g.a", "missing (falls back to en)"),
    ]

def test_repo_locales_have_no_errors():
    # Intentionally errors only: warnings depend on translation progress.
    assert [i for i in check.check() if i.level == "error"] == []

def test_missing_locale_json_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "ui.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "locale.json", "", "file not found"),
    ]

def test_invalid_json_in_locale_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text("invalid json", encoding="utf-8")
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "locale.json", "", "Expecting value: line 1 column 1 (char 0)"),
        Issue("warning", "xx", "ui.json", "a", "missing (falls back to en)"),
    ]

def test_non_object_locale_json_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "locale.json", "", "must be a JSON object"),
        Issue("warning", "xx", "ui.json", "a", "missing (falls back to en)"),
    ]

def test_missing_required_metadata_field_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    incomplete_meta = {k: v for k, v in {"code": "xx", **META}.items() if k != "name"}
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps(incomplete_meta), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "locale.json", "name", "missing field"),
    ]

def test_code_mismatch_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps({"code": "yy", **META}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    assert check.check(None, tmp_path) == [
        Issue("error", "xx", "locale.json", "code", "must match directory name"),
    ]

def test_non_string_value_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": 123})
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "ui.json", "a", "value must be a string"),
    ]

def test_discover_skips_broken_locale(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "gd", {"a": "A"})
    d = tmp_path / "broken"; d.mkdir()
    (d / "locale.json").write_text("invalid", encoding="utf-8")
    result = discover(tmp_path)
    assert sorted(result) == ["en", "gd"]

def test_discover_skips_mismatched_code(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps({"code": "yy", **META}), encoding="utf-8")
    result = discover(tmp_path)
    assert sorted(result) == ["en"]

def test_summary_includes_missing_count(tmp_path):
    write(tmp_path, "en", {"a": "A", "b": "B", "c": "C"})
    write(tmp_path, "xx", {"a": "X"})
    summary = check.summary("xx", tmp_path)
    assert summary == ["xx ui.json: 33.3% complete (2 missing)"]

def test_check_on_nonexistent_root_returns_empty(tmp_path):
    nonexistent = tmp_path / "does_not_exist"
    issues = check.check(None, nonexistent)
    assert issues == []

def test_cli_check_returns_1_on_error(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "X", "b": "Y"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check"])
    captured = capsys.readouterr()
    assert result == 1
    assert captured.out.splitlines() == [
        "ERROR   xx/ui.json b: key not in en",
        "xx ui.json: 100.0% complete (0 missing)",
    ]

def test_cli_check_returns_0_on_clean(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "X"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check"])
    captured = capsys.readouterr()
    assert result == 0
    assert captured.out.splitlines() == ["xx ui.json: 100.0% complete (0 missing)"]

def test_cli_quiet_suppresses_warnings(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A", "b": "B"})
    write(tmp_path, "xx", {"a": "X"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check", "--quiet"])
    captured = capsys.readouterr()
    assert result == 0
    assert captured.out.splitlines() == ["xx ui.json: 50.0% complete (1 missing)"]

def test_cli_quiet_with_error_still_prints_error(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A", "b": "B"})
    write(tmp_path, "xx", {"a": "X", "c": "extra"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check", "--quiet"])
    captured = capsys.readouterr()
    assert result == 1
    assert captured.out.splitlines() == [
        "ERROR   xx/ui.json c: key not in en",
        "xx ui.json: 50.0% complete (1 missing)",
    ]

def test_cli_check_with_lang_argument(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "X"})
    write(tmp_path, "yy", {"a": "X", "b": "Y"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    assert main(["check", "--lang", "xx"]) == 0
    assert capsys.readouterr().out.splitlines() == ["xx ui.json: 100.0% complete (0 missing)"]
    assert main(["check", "--lang", "yy"]) == 1
    assert capsys.readouterr().out.splitlines() == [
        "ERROR   yy/ui.json b: key not in en",
        "yy ui.json: 100.0% complete (0 missing)",
    ]

def test_cli_new_language_with_invalid_code(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["new-language", "invalid_code", "--name", "Test", "--native", "Teszt"])
    captured = capsys.readouterr()
    assert result == 1
    assert captured.out.splitlines() == ["Error: Invalid code 'invalid_code'; must match ^[a-z]{2,3}(-[A-Z]{2})?$"]

def test_cli_new_language_when_exists(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "A"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["new-language", "xx", "--name", "Test", "--native", "Teszt"])
    captured = capsys.readouterr()
    assert result == 1
    assert captured.out.splitlines() == [f"Error: {tmp_path / 'xx'} already exists"]

def test_new_language_validates_code(tmp_path, monkeypatch):
    write(tmp_path, "en", {"a": "A"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    check.new_language("fr", "French", "Français", tmp_path)
    check.new_language("pt-BR", "Portuguese", "Português", tmp_path)
    with pytest.raises(ValueError, match=re.escape("Invalid code 'invalid'; must match ^[a-z]{2,3}(-[A-Z]{2})?$")):
        check.new_language("invalid", "X", "X", tmp_path)
    assert not (tmp_path / "invalid").exists()

def test_non_string_falsy_value_no_extra_warning(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": 0})
    issues = check.check("xx", tmp_path)
    assert issues == [Issue("error", "xx", "ui.json", "a", "value must be a string")]

def test_malformed_catalog_reports_single_error(tmp_path):
    write(tmp_path, "en", {"a": "A"}); write(tmp_path, "xx", {"a": "A"})
    (tmp_path / "xx" / "ui.json").write_text("{broken", encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert len(issues) == 1 and issues[0].level == "error" and issues[0].file == "ui.json"

def test_non_object_catalog_reports_error(tmp_path):
    write(tmp_path, "en", {"a": "A"}); write(tmp_path, "xx", [1])
    assert check.check("xx", tmp_path) == [Issue("error", "xx", "ui.json", "", "catalog must be a JSON object")]

def test_invalid_locale_code_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"}); write(tmp_path, "EN_us", {"a": "A"})
    msgs = [i for i in check.check("EN_us", tmp_path) if i.key == "code"]
    assert len(msgs) == 1 and msgs[0].level == "error" and "invalid code" in msgs[0].message
