"""Strict localized prompt catalogs for generated test data (locales/<lang>/prompts.yaml).

Unlike the UI catalogs there is no English fallback: a missing or empty key raises
KeyError("<lang>:<key>") so a language never silently mixes into another's test data.
Placeholders use Python str.format syntax ({name}; literal braces as {{ and }}).
"""
from __future__ import annotations
from pathlib import Path
import yaml
from arena.i18n.locales import LOCALES

FILE = "prompts.yaml"
_cache: dict[tuple[Path, str], dict] = {}

def _root() -> Path: return LOCALES  # module global read at call time so tests can monkeypatch it

def _load(lang: str) -> dict | None:
    root = _root()
    if (root, lang) not in _cache:
        path = root / lang / FILE
        data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
        _cache[(root, lang)] = data if isinstance(data, dict) else None
    return _cache[(root, lang)]

def clear_cache() -> None: _cache.clear()

def has_language(lang: str) -> bool: return (_root() / lang / FILE).exists()

def _node(lang: str, key: str):
    node = _load(lang)
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node: raise KeyError(f"{lang}:{key}")
        node = node[part]
    return node

def prompt(lang: str, key: str, **params) -> str:
    value = _node(lang, key)
    if not isinstance(value, str) or not value: raise KeyError(f"{lang}:{key}")
    return value.format(**params)

def labels(lang: str, group: str) -> dict[str, str]:
    key = f"labels.{group}"
    mapping = _node(lang, key)
    if not isinstance(mapping, dict): raise KeyError(f"{lang}:{key}")
    for label_id, value in mapping.items():
        if not isinstance(value, str) or not value: raise KeyError(f"{lang}:{key}.{label_id}")
    return dict(mapping)
