from __future__ import annotations
import json
import re
from pathlib import Path
from arena.config import ROOT

LOCALES = ROOT / "locales"
CODE_PATTERN = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?$")
PLURAL_SUFFIXES = ("_zero", "_one", "_two", "_few", "_many", "_other")

def discover(root: Path | None = None) -> dict[str, dict]:
    root = root or LOCALES
    out = {}
    for meta in sorted(root.glob("*/locale.json")):
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "code" in data:
                # Skip if code doesn't match directory name
                if data["code"] == meta.parent.name and isinstance(data["code"], str) and CODE_PATTERN.match(data["code"]):
                    out[data["code"]] = data
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
            pass
    return out

def load_catalog(code: str, name: str = "ui", root: Path | None = None) -> dict:
    root = root or LOCALES
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

def completeness(code: str, name: str = "ui", root: Path | None = None) -> float:
    try: source = flatten(load_catalog("en", name, root))
    except (ValueError, OSError, AttributeError): return 0.0
    try: target = flatten(load_catalog(code, name, root))
    except (ValueError, OSError, AttributeError): return 0.0
    groups: dict[str, bool] = {}
    for key in source:
        base = base_key(key)
        # A plural group counts once and is translated when its "_other" form is.
        groups[base] = bool(target.get(base + "_other")) if base != key else bool(target.get(key))
    return sum(groups.values()) / len(groups) if groups else 1.0

def available(root: Path | None = None) -> list[dict]:
    root = root or LOCALES
    found = discover(root)
    order = sorted(found, key=lambda c: (c != "en", c))
    return [{k: found[c].get(k) for k in ("code", "name", "nativeName", "status")} | {"completeness": round(completeness(c, root=root), 4)} for c in order]
