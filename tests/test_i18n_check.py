import json
from unittest.mock import patch
from arena.i18n import check
from arena.i18n.__main__ import main
from arena.i18n.locales import discover

META = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}

def write(root, code, ui, meta=None):
    d = root / code; d.mkdir(parents=True, exist_ok=True)
    (d / "locale.json").write_text(json.dumps({"code": code, **(META if meta is None else meta)}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps(ui), encoding="utf-8")

def levels(issues): return sorted((i.level, i.key) for i in issues)

# Original tests
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
    issues = check.check("xx", tmp_path)
    assert [i for i in issues if i.level == "error" and i.key == "n" and "plural" in i.message]

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

# New comprehensive tests per review feedback

def test_missing_locale_json_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "ui.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert any(i.level == "error" and i.file == "locale.json" and "not found" in i.message for i in issues)

def test_invalid_json_in_locale_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text("invalid json", encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert any(i.level == "error" and i.file == "locale.json" for i in issues)

def test_non_object_locale_json_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert any(i.level == "error" and i.file == "locale.json" and "object" in i.message for i in issues)

def test_missing_required_metadata_field_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    incomplete_meta = {k: v for k, v in {"code": "xx", **META}.items() if k != "name"}
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps(incomplete_meta), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert any(i.level == "error" and i.file == "locale.json" and i.key == "name" and "missing" in i.message for i in issues)

def test_code_mismatch_without_lang_argument_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir(parents=True)
    (d / "locale.json").write_text(json.dumps({"code": "yy", **META}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    issues = check.check(None, tmp_path)  # No lang specified, so checks all directories
    # Should report error that code doesn't match directory name
    assert any(i.level == "error" and i.file == "locale.json" and "match directory" in i.message for i in issues)

def test_non_string_value_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": 123})
    issues = check.check("xx", tmp_path)
    assert any(i.level == "error" and i.file == "ui.json" and i.key == "a" and "string" in i.message for i in issues)

def test_discover_skips_broken_locale(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "good", {"a": "A"})
    # Create broken locale
    d = tmp_path / "broken"; d.mkdir()
    (d / "locale.json").write_text("invalid", encoding="utf-8")
    result = discover(tmp_path)
    # Should have en and good, but not broken
    assert "en" in result
    assert "good" in result
    assert "broken" not in result

def test_summary_includes_missing_count(tmp_path):
    write(tmp_path, "en", {"a": "A", "b": "B", "c": "C"})
    write(tmp_path, "xx", {"a": "X"})  # Missing b and c
    summary = check.summary("xx", tmp_path)
    assert len(summary) == 1
    assert "100.0% complete (2 missing)" in summary[0] or "33.3% complete (2 missing)" in summary[0]

def test_cli_check_returns_1_on_error(tmp_path, monkeypatch):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "X", "b": "Y"})  # Extra key b
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check"])
    assert result == 1

def test_cli_check_returns_0_on_clean(tmp_path, monkeypatch):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "X"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check"])
    assert result == 0

def test_cli_quiet_suppresses_warnings(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A", "b": "B"})
    write(tmp_path, "xx", {"a": "X"})  # Missing b (warning)
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    main(["check", "--quiet"])
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    assert "ui.json:" in captured.out  # Summary line should still print

def test_cli_check_with_lang_argument(tmp_path, monkeypatch):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "X"})
    write(tmp_path, "yy", {"a": "X", "b": "Y"})  # Error
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check", "--lang", "xx"])
    assert result == 0
    result = main(["check", "--lang", "yy"])
    assert result == 1

def test_cli_new_language_with_invalid_code(tmp_path, monkeypatch):
    write(tmp_path, "en", {"a": "A"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["new-language", "invalid_code", "--name", "Test", "--native", "Teszt"])
    assert result == 1

def test_cli_new_language_when_exists(tmp_path, monkeypatch):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "A"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["new-language", "xx", "--name", "Test", "--native", "Teszt"])
    assert result == 1

def test_new_language_validates_code(tmp_path, monkeypatch):
    write(tmp_path, "en", {"a": "A"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    # Valid codes
    check.new_language("fr", "French", "Français", tmp_path)
    check.new_language("pt-BR", "Portuguese", "Português", tmp_path)
    # Invalid codes
    try:
        check.new_language("invalid", "X", "X", tmp_path)
        assert False, "Should raise ValueError"
    except ValueError:
        pass

def test_non_string_falsy_value_no_extra_warning(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": 0})  # Non-string falsy
    issues = check.check("xx", tmp_path)
    # Should only have one error (not a string), not an additional warning
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    assert len(errors) == 1
    assert len(warnings) == 0
