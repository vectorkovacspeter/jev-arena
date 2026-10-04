"""Locale bundles shared by the API, CLI tools and report exporters."""
from arena.i18n.locales import available
from arena.i18n.settings import get_language, set_language

__all__ = ["available", "get_language", "set_language"]
