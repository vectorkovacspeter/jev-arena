from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Literal, NamedTuple
from arena.i18n.locales import LOCALES, base_key, completeness, discover, flatten, load_catalog

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
    except (FileNotFoundError, json.JSONDecodeError) as e: return [Issue("error", code, "locale.json", "", str(e))]
    out = [Issue("error", code, "locale.json", k, "missing field") for k in REQUIRED_META if k not in meta]
    if meta.get("status") not in ("complete", "beta"): out.append(Issue("error", code, "locale.json", "status", "must be complete or beta"))
    if meta.get("code") != code: out.append(Issue("error", code, "locale.json", "code", "must match directory name"))
    return out

def _check_catalog(code: str, name: str, root: Path) -> list[Issue]:
    file = f"{name}.json"
    source, target = flatten(load_catalog("en", name, root)), flatten(load_catalog(code, name, root))
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
        if not target.get(key): out.append(Issue("warning", code, file, key, "missing (falls back to en)"))
    return out

def check(lang: str | None = None, root: Path = LOCALES) -> list[Issue]:
    codes = [lang] if lang else [c for c in discover(root) if c != "en"]
    out = []
    for code in codes:
        out += _check_meta(code, root)
        for name in CATALOGS: out += _check_catalog(code, name, root)
    return out

def _blank(catalog: dict) -> dict:
    return {k: _blank(v) if isinstance(v, dict) else "" for k, v in catalog.items()}

def new_language(code: str, name: str, native: str, root: Path = LOCALES) -> Path:
    target = root / code
    if target.exists(): raise FileExistsError(f"{target} already exists")
    target.mkdir(parents=True)
    meta = {"code": code, "name": name, "nativeName": native, "status": "beta", "review": "needs native review", "dir": "ltr"}
    (target / "locale.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for catalog in CATALOGS:
        (target / f"{catalog}.json").write_text(json.dumps(_blank(load_catalog("en", catalog, root)), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target

def summary(lang: str | None = None, root: Path = LOCALES) -> list[str]:
    codes = [lang] if lang else [c for c in discover(root) if c != "en"]
    return [f"{c} {n}.json: {completeness(c, n, root) * 100:.1f}% complete" for c in codes for n in CATALOGS]
