from __future__ import annotations
import json
from arena.config import DATA, write_json
from arena.i18n.locales import discover

SETTINGS = DATA / "settings.json"
DEFAULT = "en"

def _read() -> dict:
    try: data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}
    return data if isinstance(data, dict) else {}

def get_language() -> str:
    code = _read().get("language", DEFAULT)
    return code if isinstance(code, str) and code in discover() else DEFAULT

def set_language(code: str) -> str:
    if code not in discover(): raise ValueError(f"Unknown language: {code}")
    write_json(SETTINGS, {**_read(), "language": code})
    return code
