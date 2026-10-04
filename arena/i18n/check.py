from __future__ import annotations
import json
import re
import string
from pathlib import Path
from typing import Literal, NamedTuple
import yaml
from arena.i18n.locales import CODE_PATTERN, LOCALES, base_key, completeness, discover, flatten, load_catalog

REQUIRED_META = ("code", "name", "nativeName", "status", "review", "dir")
CATALOGS = ("ui",)  # Phase 2 adds "report".
PROMPT_CATALOGS = ("prompts",)  # Strict YAML catalogs for test data; checked only when en has one.
PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")

class Issue(NamedTuple):
    level: Literal["error", "warning"]
    lang: str
    file: str
    key: str
    message: str

def _placeholders(value: str) -> set[str]: return set(PLACEHOLDER.findall(value))

def _check_meta(code: str, root: Path) -> list[Issue]:
    path = root / code / "locale.json"
    try: meta = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError: return [Issue("error", code, "locale.json", "", "file not found")]
    except (json.JSONDecodeError, UnicodeDecodeError) as e: return [Issue("error", code, "locale.json", "", str(e))]
    if not isinstance(meta, dict): return [Issue("error", code, "locale.json", "", "must be a JSON object")]
    out = [Issue("error", code, "locale.json", k, "missing field") for k in REQUIRED_META if k not in meta]
    if meta.get("status") not in ("complete", "beta"): out.append(Issue("error", code, "locale.json", "status", "must be complete or beta"))
    if meta.get("code") != code: out.append(Issue("error", code, "locale.json", "code", "must match directory name"))
    if not isinstance(meta.get("code"), str) or not CODE_PATTERN.match(meta["code"]): out.append(Issue("error", code, "locale.json", "code", "invalid code; must match ^[a-z]{2,3}(-[A-Z]{2})?$"))
    return out

def _check_catalog(code: str, name: str, root: Path) -> list[Issue]:
    file = f"{name}.json"
    try:
        source, target = flatten(load_catalog("en", name, root)), flatten(load_catalog(code, name, root))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        return [Issue("error", code, file, "", f"cannot read catalog: {e}")]
    except AttributeError:
        return [Issue("error", code, file, "", "catalog must be a JSON object")]
    out = []
    for key, value in target.items():
        if key not in source: out.append(Issue("error", code, file, key, "key not in en")); continue
        if not isinstance(value, str): out.append(Issue("error", code, file, key, "value must be a string")); continue
        if value and _placeholders(value) != _placeholders(source[key]):
            out.append(Issue("error", code, file, key, f"placeholders {sorted(_placeholders(value))} != en {sorted(_placeholders(source[key]))}"))
    plural_groups = {base_key(k) for k in source if base_key(k) != k}
    for group in plural_groups:
        forms = [k for k in target if base_key(k) == group and target[k]]
        if forms and not target.get(group + "_other"): out.append(Issue("error", code, file, group, "plural group needs an _other form"))
    for key in source:
        if base_key(key) in plural_groups and not key.endswith("_other"): continue
        if key not in target or (isinstance(target.get(key), str) and not target.get(key)):
            out.append(Issue("warning", code, file, key, "missing (falls back to en)"))
    return out

def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def _yaml_leaves(node: dict, prefix: str = "") -> tuple[dict, list[str]]:
    """Flatten a YAML mapping; also return dotted paths of non-string keys."""
    leaves, bad = {}, []
    for key, value in node.items():
        full = f"{prefix}{key}"
        if not isinstance(key, str): bad.append(full); continue
        if isinstance(value, dict):
            sub, sub_bad = _yaml_leaves(value, full + ".")
            leaves.update(sub); bad += sub_bad
        else: leaves[full] = value
    return leaves, bad

def _format_fields(value: str) -> set[str]:
    """Python str.format field names (root names only); raises ValueError on a malformed template."""
    return {re.split(r"[.\[]", f)[0] for _, f, _, _ in string.Formatter().parse(value) if f is not None}

def _label_groups(catalog: dict) -> dict:
    groups = catalog.get("labels")
    return {k: v for k, v in groups.items() if isinstance(v, dict)} if isinstance(groups, dict) else {}

def _prompt_state(code: str, name: str, root: Path):
    """(en catalog, target catalog or None, blocking issue or None); en catalog is None when en has no such file."""
    file = f"{name}.yaml"
    en_path, path = root / "en" / file, root / code / file
    if not en_path.exists(): return None, None, None
    try: source = _load_yaml(en_path)
    except (yaml.YAMLError, UnicodeDecodeError, OSError) as e: return {}, None, Issue("error", code, file, "", f"cannot read en catalog: {e}")
    if not isinstance(source, dict): return {}, None, Issue("error", code, file, "", "en catalog must be a mapping")
    if not path.exists(): return source, None, Issue("warning", code, file, "", f"{file} missing (test data unavailable in this language)")
    try: target = _load_yaml(path)
    except (yaml.YAMLError, UnicodeDecodeError, OSError) as e: return source, None, Issue("error", code, file, "", f"cannot read catalog: {e}")
    if not isinstance(target, dict): return source, None, Issue("error", code, file, "", "catalog must be a mapping")
    return source, target, None

def _check_prompts(code: str, name: str, root: Path) -> list[Issue]:
    file = f"{name}.yaml"
    source_tree, target_tree, issue = _prompt_state(code, name, root)
    if source_tree is None: return []
    if issue: return [issue]
    source, _ = _yaml_leaves(source_tree)
    target, bad_keys = _yaml_leaves(target_tree)
    out = [Issue("error", code, file, k, "key must be a string") for k in bad_keys]
    en_groups, groups = _label_groups(source_tree), _label_groups(target_tree)
    in_group = lambda key: key.startswith("labels.") and key.split(".")[1] in en_groups and key.split(".")[1] in groups
    for key, value in target.items():
        if key not in source:
            if not in_group(key): out.append(Issue("error", code, file, key, "key not in en"))
            continue
        if not isinstance(value, str): out.append(Issue("error", code, file, key, "value must be a string")); continue
        if not value: continue
        try: fields = _format_fields(value)
        except ValueError as e: out.append(Issue("error", code, file, key, f"invalid format string: {e}")); continue
        expected = _format_fields(source[key])
        if fields != expected: out.append(Issue("error", code, file, key, f"placeholders {sorted(fields)} != en {sorted(expected)}"))
    for key in source:
        if key not in target:
            if not in_group(key): out.append(Issue("error", code, file, key, "missing (test data generation would fail)"))
        elif target[key] == "": out.append(Issue("warning", code, file, key, "empty (test data generation would fail)"))
    for group, en_labels in en_groups.items():
        labels = groups.get(group)
        if labels is None: continue
        missing, extra = sorted(set(en_labels) - set(labels), key=str), sorted(set(labels) - set(en_labels), key=str)
        if missing or extra: out.append(Issue("error", code, file, f"labels.{group}", f"label ids differ from en: missing {missing}, extra {extra}"))
        values = [v for v in labels.values() if isinstance(v, str) and v]
        dupes = sorted({v for v in values if values.count(v) > 1})
        if dupes: out.append(Issue("error", code, file, f"labels.{group}", f"duplicate localized labels {dupes}"))
    return out

def _prompt_summary(code: str, name: str, root: Path) -> str | None:
    source_tree, target_tree, _ = _prompt_state(code, name, root)
    if not source_tree: return None
    source, _ = _yaml_leaves(source_tree)
    target = _yaml_leaves(target_tree)[0] if target_tree is not None else {}
    missing = sum(1 for k in source if not (isinstance(target.get(k), str) and target[k]))
    pct = (len(source) - missing) / len(source) * 100 if source else 100.0
    return f"{code} {name}.yaml: {pct:.1f}% complete ({missing} missing)"

def check(lang: str | None = None, root: Path | None = None) -> list[Issue]:
    if root is None: root = LOCALES
    if not root.exists():
        return []
    if lang:
        codes = [lang]
    else:
        # Iterate directory names, not discover(), to catch broken locales
        codes = sorted([d.name for d in root.iterdir() if d.is_dir() and d.name != "en"])
    out = []
    for code in codes:
        out += _check_meta(code, root)
        for name in CATALOGS: out += _check_catalog(code, name, root)
        for name in PROMPT_CATALOGS: out += _check_prompts(code, name, root)
    return out

def _blank(catalog: dict) -> dict:
    return {k: _blank(v) if isinstance(v, dict) else "" for k, v in catalog.items()}

def new_language(code: str, name: str, native: str, root: Path | None = None) -> Path:
    if root is None: root = LOCALES
    if not CODE_PATTERN.match(code):
        raise ValueError(f"Invalid code '{code}'; must match ^[a-z]{{2,3}}(-[A-Z]{{2}})?$")
    target = root / code
    if target.exists(): raise FileExistsError(f"{target} already exists")
    target.mkdir(parents=True)
    meta = {"code": code, "name": name, "nativeName": native, "status": "beta", "review": "needs native review", "dir": "ltr"}
    (target / "locale.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for catalog in CATALOGS:
        (target / f"{catalog}.json").write_text(json.dumps(_blank(load_catalog("en", catalog, root)), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for catalog in PROMPT_CATALOGS:
        en_path = root / "en" / f"{catalog}.yaml"
        if en_path.exists():
            blank = _blank(_load_yaml(en_path) or {})
            (target / f"{catalog}.yaml").write_text(yaml.safe_dump(blank, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    return target

def _count_missing(lang: str, name: str, root: Path | None = None) -> int:
    """Count missing/empty keys (warnings) for a locale and catalog."""
    if root is None: root = LOCALES
    issues = _check_catalog(lang, name, root)
    return sum(1 for i in issues if i.level == "warning")

def summary(lang: str | None = None, root: Path | None = None) -> list[str]:
    if root is None: root = LOCALES
    if lang:
        codes = [lang]
    else:
        codes = sorted([d.name for d in root.iterdir() if d.is_dir() and d.name != "en"])
    lines = []
    for c in codes:
        for n in CATALOGS:
            missing = _count_missing(c, n, root)
            pct = completeness(c, n, root) * 100
            lines.append(f"{c} {n}.json: {pct:.1f}% complete ({missing} missing)")
        for n in PROMPT_CATALOGS:
            line = _prompt_summary(c, n, root)
            if line: lines.append(line)
    return lines
