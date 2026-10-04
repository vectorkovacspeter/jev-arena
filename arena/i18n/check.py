from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Literal, NamedTuple
from arena.i18n.locales import CODE_PATTERN, LOCALES, base_key, completeness, discover, flatten, load_catalog

REQUIRED_META = ("code", "name", "nativeName", "status", "review", "dir")
CATALOGS = ("ui",)  # Phase 2 adds "report".
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
    return lines
