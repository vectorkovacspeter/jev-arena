from __future__ import annotations
import json
from pathlib import Path
from arena.config import ROOT

LOCALES = ROOT / "locales"
PLURAL_SUFFIXES = ("_zero", "_one", "_two", "_few", "_many", "_other")

def discover(root: Path = LOCALES) -> dict[str, dict]:
    out = {}
    for meta in sorted(root.glob("*/locale.json")):
        data = json.loads(meta.read_text(encoding="utf-8"))
        out[data["code"]] = data
    return out

def load_catalog(code: str, name: str = "ui", root: Path = LOCALES) -> dict:
    path = root / code / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def flatten(catalog: dict, prefix: str = "") -> dict[str, str]:
    out = {}
    for key, value in catalog.items():
        full = f"{prefix}{key}"
        if isinstance(value, dict): out.update(flatten(value, full + "."))
        else: out[full] = value
    return out

def base_key(key: str) -> str:
    for suffix in PLURAL_SUFFIXES:
        if key.endswith(suffix): return key[: -len(suffix)]
    return key

def completeness(code: str, name: str = "ui", root: Path = LOCALES) -> float:
    source = flatten(load_catalog("en", name, root))
    target = flatten(load_catalog(code, name, root))
    groups: dict[str, bool] = {}
    for key in source:
        base = base_key(key)
        # A plural group counts once and is translated when its "_other" form is.
        groups[base] = bool(target.get(base + "_other")) if base != key else bool(target.get(key))
    return sum(groups.values()) / len(groups) if groups else 1.0

def available(root: Path = LOCALES) -> list[dict]:
    found = discover(root)
    order = sorted(found, key=lambda c: (c != "en", c))
    return [{k: found[c].get(k) for k in ("code", "name", "nativeName", "status")} | {"completeness": round(completeness(c, root=root), 4)} for c in order]
