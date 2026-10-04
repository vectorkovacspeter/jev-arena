import pytest
from arena.i18n import settings

@pytest.fixture(autouse=True)
def english_settings(tmp_path_factory, monkeypatch):
    """Tests never read the user's .arena/settings.json: the language is English unless a test sets it."""
    monkeypatch.setattr(settings, "SETTINGS", tmp_path_factory.mktemp("settings") / "settings.json")
