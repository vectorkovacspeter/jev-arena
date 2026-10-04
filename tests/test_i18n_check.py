import json
from arena.i18n import check
from arena.i18n.__main__ import main
from arena.i18n.locales import discover

META = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}

def write(root, code, ui, meta=None):
    d = root / code; d.mkdir(parents=True, exist_ok=True)
    (d / "locale.json").write_text(json.dumps({"code": code, **(META if meta is None else meta)}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps(ui), encoding="utf-8")

# Test: clean locale
def test_clean_locale_has_no_issues(tmp_path):
    write(tmp_path, "en", {"a": "Hi {{name}}"})
    write(tmp_path, "xx", {"a": "Szia {{name}}"})
    assert check.check("xx", tmp_path) == []

# Test: extra key and placeholder mismatch
def test_extra_key_and_placeholder_mismatch_are_errors(tmp_path):
    write(tmp_path, "en", {"a": "Hi {{name}}"})
    write(tmp_path, "xx", {"a": "Szia {{nev}}", "z": "x"})
    issues = check.check("xx", tmp_path)
    assert len(issues) == 2
    assert issues[0].level == "error"
    assert issues[0].file == "ui.json"
    assert issues[0].key == "a"
    assert issues[0].message == "placeholders ['nev'] != en ['name']"
    assert issues[1].level == "error"
    assert issues[1].file == "ui.json"
    assert issues[1].key == "z"
    assert issues[1].message == "key not in en"

# Test: missing and empty are warnings
def test_missing_and_empty_are_warnings(tmp_path):
    write(tmp_path, "en", {"a": "A", "b": "B"})
    write(tmp_path, "xx", {"a": ""})
    issues = check.check("xx", tmp_path)
    assert len(issues) == 2
    assert issues[0].level == "warning"
    assert issues[0].file == "ui.json"
    assert issues[0].key == "a"
    assert issues[0].message == "missing (falls back to en)"
    assert issues[1].level == "warning"
    assert issues[1].file == "ui.json"
    assert issues[1].key == "b"
    assert issues[1].message == "missing (falls back to en)"

# Test: plural group needs _other
def test_plural_group_needs_other(tmp_path):
    write(tmp_path, "en", {"n_one": "x", "n_other": "xs"})
    write(tmp_path, "xx", {"n_one": "y"})
    issues = check.check("xx", tmp_path)
    assert len(issues) == 2
    assert issues[0].level == "error"
    assert issues[0].file == "ui.json"
    assert issues[0].key == "n"
    assert issues[0].message == "plural group needs an _other form"
    assert issues[1].level == "warning"
    assert issues[1].file == "ui.json"
    assert issues[1].key == "n_other"
    assert issues[1].message == "missing (falls back to en)"

# Test: bad metadata
def test_bad_metadata_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "A"}, meta={**META, "status": "done"})
    issues = check.check("xx", tmp_path)
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert issues[0].file == "locale.json"
    assert issues[0].key == "status"
    assert issues[0].message == "must be complete or beta"

# Test: new language scaffold
def test_new_language_scaffold_is_valid_and_empty(tmp_path):
    write(tmp_path, "en", {"g": {"a": "A {{n}}"}})
    check.new_language("xx", "Example", "Exemplum", tmp_path)
    assert json.loads((tmp_path / "xx" / "ui.json").read_text(encoding="utf-8")) == {"g": {"a": ""}}
    assert json.loads((tmp_path / "xx" / "locale.json").read_text(encoding="utf-8"))["status"] == "beta"
    # Check that all issues are warnings (empty scaffold)
    issues = check.check("xx", tmp_path)
    assert all(i.level == "warning" for i in issues)

# Test: repo locales have no errors
def test_repo_locales_have_no_errors():
    assert [i for i in check.check() if i.level == "error"] == []

# Test: missing locale.json
def test_missing_locale_json_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "ui.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert issues[0].file == "locale.json"
    assert issues[0].message == "file not found"

# Test: invalid JSON in locale
def test_invalid_json_in_locale_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text("invalid json", encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert len(issues) == 2
    assert issues[0].level == "error"
    assert issues[0].file == "locale.json"
    assert issues[0].message.startswith("Expecting value")
    assert issues[1].level == "warning"
    assert issues[1].file == "ui.json"
    assert issues[1].key == "a"
    assert issues[1].message == "missing (falls back to en)"

# Test: non-object locale JSON
def test_non_object_locale_json_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert len(issues) == 2
    assert issues[0].level == "error"
    assert issues[0].file == "locale.json"
    assert issues[0].message == "must be a JSON object"
    assert issues[1].level == "warning"
    assert issues[1].file == "ui.json"
    assert issues[1].key == "a"
    assert issues[1].message == "missing (falls back to en)"

# Test: missing required metadata field
def test_missing_required_metadata_field_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    incomplete_meta = {k: v for k, v in {"code": "xx", **META}.items() if k != "name"}
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps(incomplete_meta), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert issues[0].file == "locale.json"
    assert issues[0].key == "name"
    assert issues[0].message == "missing field"

# Test: code mismatch
def test_code_mismatch_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps({"code": "yy", **META}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps({"a": "A"}), encoding="utf-8")
    issues = check.check(None, tmp_path)
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert issues[0].file == "locale.json"
    assert issues[0].key == "code"
    assert issues[0].message == "must match directory name"

# Test: non-string value
def test_non_string_value_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": 123})
    issues = check.check("xx", tmp_path)
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert issues[0].file == "ui.json"
    assert issues[0].key == "a"
    assert issues[0].message == "value must be a string"

# Test: discover skips broken locale
def test_discover_skips_broken_locale(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "good", {"a": "A"})
    d = tmp_path / "broken"; d.mkdir()
    (d / "locale.json").write_text("invalid", encoding="utf-8")
    result = discover(tmp_path)
    assert "en" in result
    assert "good" in result
    assert "broken" not in result

# Test: discover skips mismatched code
def test_discover_skips_mismatched_code(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    d = tmp_path / "xx"; d.mkdir()
    (d / "locale.json").write_text(json.dumps({"code": "yy", **META}), encoding="utf-8")
    result = discover(tmp_path)
    assert "en" in result
    assert "xx" not in result
    assert "yy" not in result

# Test: summary includes missing count
def test_summary_includes_missing_count(tmp_path):
    write(tmp_path, "en", {"a": "A", "b": "B", "c": "C"})
    write(tmp_path, "xx", {"a": "X"})
    summary = check.summary("xx", tmp_path)
    assert len(summary) == 1
    assert summary[0] == "xx ui.json: 33.3% complete (2 missing)"

# Test: check on nonexistent root returns empty
def test_check_on_nonexistent_root_returns_empty(tmp_path):
    nonexistent = tmp_path / "does_not_exist"
    issues = check.check(None, nonexistent)
    assert issues == []

# Test: CLI check returns 1 on error with exact output
def test_cli_check_returns_1_on_error(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "X", "b": "Y"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check"])
    captured = capsys.readouterr()
    assert result == 1
    lines = captured.out.splitlines()
    assert len(lines) == 2
    assert lines[0] == "ERROR   xx/ui.json b: key not in en"
    assert lines[1] == "xx ui.json: 100.0% complete (0 missing)"

# Test: CLI check returns 0 on clean with exact output
def test_cli_check_returns_0_on_clean(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "X"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check"])
    captured = capsys.readouterr()
    assert result == 0
    lines = captured.out.splitlines()
    assert len(lines) == 1
    assert lines[0] == "xx ui.json: 100.0% complete (0 missing)"

# Test: CLI quiet suppresses warnings
def test_cli_quiet_suppresses_warnings(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A", "b": "B"})
    write(tmp_path, "xx", {"a": "X"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check", "--quiet"])
    captured = capsys.readouterr()
    assert result == 0
    lines = captured.out.splitlines()
    assert len(lines) == 1
    assert lines[0] == "xx ui.json: 50.0% complete (1 missing)"
    assert "WARNING" not in captured.out

# Test: CLI quiet with error prints error but not warning
def test_cli_quiet_with_error_still_prints_error(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A", "b": "B"})
    write(tmp_path, "xx", {"a": "X", "c": "extra"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check", "--quiet"])
    captured = capsys.readouterr()
    assert result == 1
    lines = captured.out.splitlines()
    assert len(lines) == 2
    assert lines[0] == "ERROR   xx/ui.json c: key not in en"
    assert lines[1] == "xx ui.json: 50.0% complete (1 missing)"
    assert "WARNING" not in captured.out

# Test: CLI check with --lang argument
def test_cli_check_with_lang_argument(tmp_path, monkeypatch):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "X"})
    write(tmp_path, "yy", {"a": "X", "b": "Y"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["check", "--lang", "xx"])
    assert result == 0
    result = main(["check", "--lang", "yy"])
    assert result == 1

# Test: CLI new-language with invalid code
def test_cli_new_language_with_invalid_code(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["new-language", "invalid_code", "--name", "Test", "--native", "Teszt"])
    captured = capsys.readouterr()
    assert result == 1
    assert captured.out.startswith("Error:")

# Test: CLI new-language when exists
def test_cli_new_language_when_exists(tmp_path, monkeypatch, capsys):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": "A"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    result = main(["new-language", "xx", "--name", "Test", "--native", "Teszt"])
    captured = capsys.readouterr()
    assert result == 1
    assert captured.out.startswith("Error:")

# Test: new-language validates code
def test_new_language_validates_code(tmp_path, monkeypatch):
    write(tmp_path, "en", {"a": "A"})
    monkeypatch.setattr(check, "LOCALES", tmp_path)
    check.new_language("fr", "French", "Français", tmp_path)
    check.new_language("pt-BR", "Portuguese", "Português", tmp_path)
    try:
        check.new_language("invalid", "X", "X", tmp_path)
        assert False, "Should raise ValueError"
    except ValueError:
        pass

# Test: non-string falsy value no extra warning
def test_non_string_falsy_value_no_extra_warning(tmp_path):
    write(tmp_path, "en", {"a": "A"})
    write(tmp_path, "xx", {"a": 0})
    issues = check.check("xx", tmp_path)
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert issues[0].key == "a"
    assert issues[0].message == "value must be a string"
