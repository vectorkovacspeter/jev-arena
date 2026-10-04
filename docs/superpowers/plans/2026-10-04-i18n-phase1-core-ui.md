# i18n Phase 1: Core and UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Jev Arena UI fully translatable using a shared locale bundle and a global language setting stored on the server. Ship English and a beta Hungarian locale, plus contributor tooling that checks catalogs.

**Architecture:** Each language is a `locales/<lang>/` directory holding `locale.json` and `ui.json`. Python (`arena/i18n/`) discovers the locales, measures how complete each one is, stores the global language in `.arena/settings.json`, and exposes `GET/POST /api/i18n`. The React app uses i18next with catalogs bundled at build time through `import.meta.glob`, so the saved offline report keeps working. Locale-aware formatting goes through `apps/web/src/format.ts`, built on `Intl`. User-facing backend errors carry a stable `code` and `params` that the UI translates. The English `detail` is kept as a fallback.

**Tech Stack:** Python 3.11, FastAPI, pytest; React 19, TypeScript 5.9, Vite 6, i18next, react-i18next, i18next-parser, ESLint with eslint-plugin-i18next; Node 22 `node --test`.

Spec: `docs/superpowers/specs/2026-10-04-i18n-design.md` (section 1 and the phase-1 parts of section 4).

## Global Constraints

- `en` is the source of truth. Runtime falls back to `en` for missing keys, and an empty string counts as missing (`returnEmptyString: false`).
- Catalog format: nested JSON objects. Key separator `.`; interpolation `{{name}}`; plurals use i18next suffixes `_one` / `_other` (Hungarian uses the same two categories).
- Top-level namespaces in `ui.json`: `common`, `shell`, `nav`, `overview`, `results`, `explore`, `operations`, `replay`, `setup`, `guide`, `abcd`, `errors`, `readiness`, `packs`, `families`.
- The global setting is `{"language": "<code>"}` in `<ARENA_DATA_DIR>/settings.json` (default `.arena/settings.json`). Default is `en`.
- API: `GET /api/i18n` and `POST /api/i18n` with body `{"language": "<code>"}`. **POST, not the spec's PUT**, because the existing `api()` helper and the token/origin middleware only handle POST mutations. Update the spec line when committing Task 2.
- The English text of every existing error message stays word for word as before. Codes are added next to it, never in place of it.
- **No English test case may change.** Phase 1 must not touch `arena/fresh.py`, `arena/episodes.py`, `arena/importers.py`, `arena/multilingual.py`, `arena/abcd.py`, `arena/wire.py`, `arena/contracts.py` or `arena/scoring.py`.
- Every new Python module lives in the package `arena/i18n/`.
- Hungarian `locale.json` has `"status": "beta"` and `"review": "needs native review"`.
- Commit after each task. Run the full verification before the last commit:

```bash
uv run pytest -q
node --experimental-strip-types --test apps/web/tests/*.test.mjs
npm run build
```

## File Structure

| Path | Responsibility |
|---|---|
| `locales/en/locale.json`, `locales/hu/locale.json` | Locale metadata |
| `locales/en/ui.json`, `locales/hu/ui.json` | UI catalogs |
| `arena/i18n/__init__.py` | Package marker, re-exports `available`, `get_language`, `set_language` |
| `arena/i18n/locales.py` | Find locales, load catalogs, flatten keys, compute completeness |
| `arena/i18n/settings.py` | Read and write the global language |
| `arena/i18n/errors.py` | `ArenaError(ValueError)` with `code` and `params` |
| `arena/i18n/check.py` | Catalog validation (missing or extra keys, placeholders, plurals, metadata) |
| `arena/i18n/__main__.py` | CLI: `check`, `new-language` |
| `arena/api.py` | `/api/i18n` endpoints; coded error responses |
| `arena/controller.py`, `arena/suites.py` | Raise `ArenaError` with codes; `reason_code` in readiness |
| `apps/web/src/i18n.ts` | i18next setup, bundled resources, language switching, `useT` re-export |
| `apps/web/src/format.ts` | Pure `Intl` formatters that take a locale argument |
| `apps/web/src/labels.ts` | `packLabel`, `familyLabel`, `slug` helpers |
| `apps/web/src/LanguageSwitcher.tsx` | Header language select |
| `apps/web/src/EnglishOnly.tsx` | "English only" note for untranslated prose |
| `apps/shared/AppShell.tsx` | Accepts a `headerExtra` slot and translatable shell strings |
| `apps/web/src/navigation.ts` | `pageNames` becomes `pageKeys` (page id → catalog key) |
| `apps/web/src/*.tsx` | String extraction |
| `apps/web/tests/format.test.mjs`, `apps/web/tests/i18n.test.mjs` | Node tests |
| `tests/test_i18n_locales.py`, `tests/test_i18n_check.py`, `tests/test_i18n_api.py` | Python tests |
| `i18next-parser.config.js`, `eslint.i18n.config.js` | Tooling configs |
| `docs/i18n/CONTRIBUTING-TRANSLATIONS.md`, `docs/i18n/ARCHITECTURE.md` | Contributor docs (Phase 1 sections) |

---

### Task 1: Locale bundle and Python loader

**Files:**
- Create: `locales/en/locale.json`, `locales/en/ui.json`, `locales/hu/locale.json`, `locales/hu/ui.json`
- Create: `arena/i18n/__init__.py`, `arena/i18n/locales.py`
- Test: `tests/test_i18n_locales.py`

**Interfaces:**
- Produces:
  - `arena.i18n.locales.LOCALES: Path` (repo `locales/`)
  - `discover(root: Path = LOCALES) -> dict[str, dict]` returns code → locale.json contents
  - `load_catalog(code: str, name: str = "ui", root: Path = LOCALES) -> dict`
  - `flatten(catalog: dict, prefix: str = "") -> dict[str, str]`
  - `completeness(code: str, name: str = "ui", root: Path = LOCALES) -> float` (0..1; non-empty target keys / en keys, counting base keys of plural groups once)
  - `available(root: Path = LOCALES) -> list[dict]` returns `[{code, name, nativeName, status, completeness}]` sorted with `en` first, then by code

- [ ] **Step 1: Create the seed locale files**

`locales/en/locale.json`:
```json
{ "code": "en", "name": "English", "nativeName": "English", "status": "complete", "review": "source", "dir": "ltr" }
```
`locales/hu/locale.json`:
```json
{ "code": "hu", "name": "Hungarian", "nativeName": "Magyar", "status": "beta", "review": "needs native review", "dir": "ltr" }
```
`locales/en/ui.json` (seed; later tasks add keys):
```json
{
  "common": { "unavailable": "Unavailable", "notApplicable": "N/A", "loading": "Loading…", "dismiss": "Dismiss" },
  "shell": {
    "skipToContent": "Skip to content",
    "expandNavigation": "Expand navigation",
    "collapseNavigation": "Collapse navigation",
    "presenter": "Presenter",
    "exitPresenter": "Exit presenter",
    "exitPresenterTitle": "Exit presenter (Esc)",
    "presenterTitle": "Presenter mode",
    "workspace": "WORKSPACE",
    "localWorkspace": "Local workspace",
    "homeLabel": "The AI Automators — {{appName}} home",
    "workspaceLabel": "{{appName}} workspace",
    "navigationLabel": "{{appName}} navigation",
    "language": "Language",
    "beta": "beta",
    "englishOnly": "This section is available in English only."
  },
  "nav": {
    "arena": "Overview", "results": "Results", "cases": "Case explorer", "abcd": "Support conversations",
    "models": "Model guide", "takeaways": "What we learned", "sources": "Tests & scoring",
    "chart": "Accuracy and speed", "replay": "Workflow replays", "run": "Run a new test", "setup": "Setup",
    "previousView": "previous view"
  }
}
```
`locales/hu/ui.json`:
```json
{
  "common": { "unavailable": "Nem elérhető", "notApplicable": "N/A", "loading": "Betöltés…", "dismiss": "Bezárás" },
  "shell": {
    "skipToContent": "Ugrás a tartalomra",
    "expandNavigation": "Navigáció kinyitása",
    "collapseNavigation": "Navigáció becsukása",
    "presenter": "Bemutató",
    "exitPresenter": "Kilépés a bemutatóból",
    "exitPresenterTitle": "Kilépés a bemutatóból (Esc)",
    "presenterTitle": "Bemutató mód",
    "workspace": "MUNKATERÜLET",
    "localWorkspace": "Helyi munkaterület",
    "homeLabel": "The AI Automators — {{appName}} kezdőlap",
    "workspaceLabel": "{{appName}} munkaterület",
    "navigationLabel": "{{appName}} navigáció",
    "language": "Nyelv",
    "beta": "béta",
    "englishOnly": "Ez a rész csak angolul érhető el."
  },
  "nav": {
    "arena": "Áttekintés", "results": "Eredmények", "cases": "Esetböngésző", "abcd": "Ügyfélszolgálati beszélgetések",
    "models": "Modellkalauz", "takeaways": "Tanulságok", "sources": "Tesztek és pontozás",
    "chart": "Pontosság és sebesség", "replay": "Munkafolyamat-visszajátszás", "run": "Új teszt futtatása", "setup": "Beállítás",
    "previousView": "előző nézet"
  }
}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_i18n_locales.py`:
```python
import json
from arena.i18n import locales

def write(root, code, meta, ui):
    d = root / code; d.mkdir(parents=True)
    (d / "locale.json").write_text(json.dumps({"code": code, **meta}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps(ui), encoding="utf-8")

def test_flatten_nested_keys():
    assert locales.flatten({"a": {"b": "x", "c": {"d": "y"}}}) == {"a.b": "x", "a.c.d": "y"}

def test_completeness_counts_non_empty_and_plural_groups_once(tmp_path):
    meta = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}
    write(tmp_path, "en", meta, {"a": "A", "n_one": "{{count}} item", "n_other": "{{count}} items", "b": "B"})
    write(tmp_path, "xx", meta, {"a": "AA", "n_one": "", "n_other": "{{count}} xs", "b": ""})
    assert locales.completeness("xx", root=tmp_path) == 2 / 3

def test_available_lists_en_first(tmp_path):
    meta = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}
    write(tmp_path, "hu", meta, {"a": "A"}); write(tmp_path, "en", meta, {"a": "A"})
    assert [x["code"] for x in locales.available(tmp_path)] == ["en", "hu"]
    assert locales.available(tmp_path)[1]["completeness"] == 1.0

def test_repo_locales_load():
    found = locales.discover()
    assert {"en", "hu"} <= set(found)
    assert found["hu"]["status"] == "beta"
```

- [ ] **Step 3: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_i18n_locales.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arena.i18n'`.

- [ ] **Step 4: Implement**

`arena/i18n/__init__.py`:
```python
"""Locale bundles shared by the API, CLI tools and report exporters."""
from arena.i18n.locales import available
from arena.i18n.settings import get_language, set_language

__all__ = ["available", "get_language", "set_language"]
```
`arena/i18n/settings.py` (stub so the package imports; Task 2 replaces it):
```python
def get_language():
    return "en"

def set_language(code):
    raise NotImplementedError
```
`arena/i18n/locales.py`:
```python
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
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_i18n_locales.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add locales arena/i18n tests/test_i18n_locales.py
git commit -m "feat(i18n): add locale bundle and Python loader"
```

---

### Task 2: Global language setting and `/api/i18n`

**Files:**
- Modify: `arena/i18n/settings.py`
- Modify: `arena/api.py` (add endpoints after `/api/session`, around line 50)
- Modify: `docs/superpowers/specs/2026-10-04-i18n-design.md` (`PUT /api/i18n` → `POST /api/i18n`)
- Test: `tests/test_i18n_api.py`

**Interfaces:**
- Consumes: `arena.i18n.locales.discover`, `available`
- Produces:
  - `arena.i18n.settings.SETTINGS: Path`
  - `get_language() -> str` (falls back to `"en"` if the file is missing, invalid, or names a locale that no longer exists)
  - `set_language(code: str) -> str` (raises `ValueError` for an unknown code)
  - HTTP `GET /api/i18n` returns `{"language": str, "locales": [...available()]}`
  - HTTP `POST /api/i18n` takes `{"language": str}` and returns the same shape. Responds 400 with `code: "unknown_language"` for an unknown code (the coded response shape comes from Task 3; in this task use plain `HTTPException(400, ...)`).

- [ ] **Step 1: Write the failing tests**

`tests/test_i18n_api.py`:
```python
import pytest
from fastapi.testclient import TestClient
from arena.i18n import settings

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SETTINGS", tmp_path / "settings.json")
    from arena.api import app
    c = TestClient(app)
    c.headers["X-Arena-Token"] = c.get("/api/session").json()["token"]
    return c

def test_default_language_is_english(client):
    body = client.get("/api/i18n").json()
    assert body["language"] == "en"
    assert {"en", "hu"} <= {x["code"] for x in body["locales"]}

def test_set_language_persists(client):
    assert client.post("/api/i18n", json={"language": "hu"}).json()["language"] == "hu"
    assert client.get("/api/i18n").json()["language"] == "hu"
    assert settings.get_language() == "hu"

def test_unknown_language_rejected(client):
    r = client.post("/api/i18n", json={"language": "xx"})
    assert r.status_code == 400
    assert client.get("/api/i18n").json()["language"] == "en"

def test_set_language_requires_token(client):
    del client.headers["X-Arena-Token"]
    assert client.post("/api/i18n", json={"language": "hu"}).status_code == 403

def test_corrupt_settings_fall_back(client):
    settings.SETTINGS.write_text("{not json", encoding="utf-8")
    assert settings.get_language() == "en"
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_i18n_api.py -v`
Expected: FAIL (`settings` has no `SETTINGS`; the endpoints return 404).

- [ ] **Step 3: Implement the settings module**

`arena/i18n/settings.py`:
```python
from __future__ import annotations
import json
from arena.config import DATA, write_json
from arena.i18n.locales import discover

SETTINGS = DATA / "settings.json"
DEFAULT = "en"

def _read() -> dict:
    try: return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return {}

def get_language() -> str:
    code = _read().get("language", DEFAULT)
    return code if code in discover() else DEFAULT

def set_language(code: str) -> str:
    if code not in discover(): raise ValueError(f"Unknown language: {code}")
    write_json(SETTINGS, {**_read(), "language": code})
    return code
```

- [ ] **Step 4: Add the endpoints to `arena/api.py`**

Add `from arena import i18n` to the imports, and insert after the `/api/session` route:
```python
@app.get("/api/i18n")
async def i18n_state():return {"language":i18n.get_language(),"locales":i18n.available()}

@app.post("/api/i18n")
async def i18n_set(request:Request):
    body=await request.json()
    try:i18n.set_language(str(body.get("language","")))
    except ValueError as e:raise HTTPException(400,str(e))
    return await i18n_state()
```
Tests monkeypatch `settings.SETTINGS`; this works through the re-exported functions because `_read` looks the module global up at call time.

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_i18n_api.py tests/test_api_security.py -v`
Expected: all pass.

- [ ] **Step 6: Update the spec and commit**

In `docs/superpowers/specs/2026-10-04-i18n-design.md`, replace `PUT /api/i18n {"language": "hu"}` with `POST /api/i18n {"language": "hu"}`, and add: "(POST because the local token/origin middleware and the UI `api()` helper treat POST as the mutation verb)".
```bash
git add arena/i18n/settings.py arena/api.py tests/test_i18n_api.py docs/superpowers/specs/2026-10-04-i18n-design.md
git commit -m "feat(i18n): global language setting and /api/i18n"
```

---

### Task 3: Coded backend errors

**Files:**
- Create: `arena/i18n/errors.py`
- Modify: `arena/api.py` (exception handler; the `HTTPException` calls with literal text at lines 71, 80, 98, 109, 123, 153-155)
- Modify: `arena/controller.py:61,72-87,304-310`
- Modify: `arena/suites.py:34,40-41`
- Test: `tests/test_i18n_errors.py`

**Interfaces:**
- Produces:
  - `class ArenaError(ValueError)` with `__init__(self, code: str, message: str, **params)`, attributes `.code`, `.params`, and `str(e) == message`
  - `class ArenaHTTPError(HTTPException)` with `__init__(self, status: int, code: str, message: str, **params)`
  - JSON error body for both: `{"detail": message, "code": code, "params": params}`
  - Readiness model entries gain `"reason_code": str | None`
- Error codes (each `en/ui.json` `errors.*` entry repeats the English text exactly, with `{{param}}` placeholders):

| Code | Raised at | English message (unchanged) | params |
|---|---|---|---|
| `duplicate_entrants` | controller.py:72 | Duplicate entrants | – |
| `unknown_entrant` | controller.py:73 | Unknown entrant | – |
| `idempotency_conflict` | controller.py:76 | Idempotency key reused with different settings | – |
| `gpu_busy_run` | controller.py:78 | Another run owns the GPU. Cancel or wait for it first. | – |
| `gpu_busy_process` | controller.py:81 | Another Arena process owns the GPU. Wait for its run to finish. | – |
| `setup_needed` | controller.py:86 | Setup needed: {{details}} | details |
| `judge_not_ready` | controller.py:87 | (judge reason, passed through) | reason |
| `run_not_found` | controller.py:304, api.py:80 | Run not found | – |
| `another_run_active` | controller.py:305 | Another run is active | – |
| `run_complete` | controller.py:306 | Run already complete | – |
| `case_manifest_modified` | controller.py:309 | Frozen case manifest was modified | – |
| `runtime_changed` | controller.py:310 | (existing text, verbatim) | – |
| `demo_needs_sources` | suites.py:34 | Demo needs the pinned public JevBench sources. Use Prepare selected in Setup first. | – |
| `suite_not_prepared` | suites.py:40 | Full suite is not prepared: {{missing}} | missing |
| `duplicate_case_ids` | suites.py:41 | Duplicate case IDs in suite | – |
| `abcd_case_not_found` | api.py:71 | ABCD case not found | – |
| `outcome_needs_model` | api.py:98 | Choose a model to filter by outcome | – |
| `case_not_found` | api.py:109 | Case not found | – |
| `invalid_event_cursor` | api.py:123 | Invalid event cursor | – |
| `choose_entrants` | api.py:153 | Choose registered entrants | – |
| `preparation_running` | api.py:154 | Preparation already running | – |
| `wait_for_active_run` | api.py:155 | Wait for the active run before changing runtime files | – |
| `unknown_language` | api.py (Task 2) | Unknown language: {{language}} | language |
| `report_read_only` | main.tsx:91 (frontend only) | This saved report is read-only. Launch Jev Arena to run models. | – |

Readiness reason codes (`readiness.*` keys): `add_typesafe_key` "Add your TypeSafe key", `native_pending` "Native integration pending", `prepare_weights` "Prepare model weights", `gpu_unavailable` "GPU worker unavailable".

- [ ] **Step 1: Write the failing tests**

`tests/test_i18n_errors.py`:
```python
import pytest
from fastapi.testclient import TestClient
from arena.i18n.errors import ArenaError
from arena import suites

def test_arena_error_is_value_error_with_original_text():
    e = ArenaError("setup_needed", "Setup needed: x", details="x")
    assert isinstance(e, ValueError) and str(e) == "Setup needed: x"
    assert e.code == "setup_needed" and e.params == {"details": "x"}

def test_suite_error_keeps_english_and_adds_code(monkeypatch):
    monkeypatch.setattr(suites, "jevbench", lambda: [])
    with pytest.raises(ArenaError) as info: suites.suite("demo")
    assert info.value.code == "demo_needs_sources"
    assert str(info.value) == "Demo needs the pinned public JevBench sources. Use Prepare selected in Setup first."

def test_http_error_body_has_code():
    from arena.api import app
    r = TestClient(app).get("/api/runs/unknown")
    assert r.status_code == 404
    assert r.json() == {"detail": "Run not found", "code": "run_not_found", "params": {}}

def test_every_code_has_english_catalog_entry():
    import re
    from arena.config import ROOT
    from arena.i18n.locales import flatten, load_catalog
    keys = flatten(load_catalog("en"))
    source = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "arena").rglob("*.py"))
    codes = set(re.findall(r"""Arena(?:HTTP)?Error\((?:\d+,\s*)?['"](?P<code>[a-z_]+)['"]""", source))
    assert codes and all(f"errors.{c}" in keys for c in codes)
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_i18n_errors.py -v`
Expected: FAIL with `ModuleNotFoundError: arena.i18n.errors`.

- [ ] **Step 3: Implement `errors.py` and the handler**

`arena/i18n/errors.py`:
```python
from fastapi import HTTPException

class ArenaError(ValueError):
    """A user-facing error: English text plus a stable code the UI translates."""
    def __init__(self, code: str, message: str, **params):
        super().__init__(message)
        self.code, self.params = code, params

class ArenaHTTPError(HTTPException):
    def __init__(self, status: int, code: str, message: str, **params):
        super().__init__(status, message)
        self.code, self.params = code, params

def body(message: str, code: str | None = None, params: dict | None = None) -> dict:
    out = {"detail": message}
    if code: out |= {"code": code, "params": params or {}}
    return out
```
In `arena/api.py`, add:
```python
from arena.i18n.errors import ArenaError,ArenaHTTPError,body as error_body

@app.exception_handler(ArenaHTTPError)
async def coded_http_error(request:Request,e:ArenaHTTPError):
    return JSONResponse(error_body(e.detail,e.code,e.params),status_code=e.status_code)

def coded(status:int,e:ValueError):
    # Preserve existing status codes; attach the code when the domain error has one.
    if isinstance(e,ArenaError):return ArenaHTTPError(status,e.code,str(e),**e.params)
    return HTTPException(status,str(e))
```
Replace each `except ValueError as e:raise HTTPException(409,str(e))` with `except ValueError as e:raise coded(409,e)` (lines 76, 148, and the Task 2 `/api/i18n` handler with 400). Replace the literal-text `HTTPException`s with `ArenaHTTPError`, for example:
```python
    if not run:raise ArenaHTTPError(404,"run_not_found","Run not found")
```
In `/api/i18n` POST, use `raise ArenaHTTPError(400,"unknown_language",str(e),language=str(body.get("language","")))`.

- [ ] **Step 4: Convert the domain raises**

In `arena/suites.py`, add `from arena.i18n.errors import ArenaError`, then:
```python
        if len(pool)<84:raise ArenaError('demo_needs_sources','Demo needs the pinned public JevBench sources. Use Prepare selected in Setup first.')
...
        if missing: raise ArenaError("suite_not_prepared","Full suite is not prepared: "+json.dumps(missing),missing=json.dumps(missing))
    if len({c.id for c in cases})!=len(cases): raise ArenaError("duplicate_case_ids","Duplicate case IDs in suite")
```
In `arena/controller.py`, do the same for every message in the table. For readiness (line 61), compute the code first, then the English reason from a dict:
```python
REASONS={"add_typesafe_key":"Add your TypeSafe key","native_pending":"Native integration pending","prepare_weights":"Prepare model weights","gpu_unavailable":"GPU worker unavailable"}
...
            reason_code=None if ready else "add_typesafe_key" if e["hosted"] else "native_pending" if e["runtime"] not in IMPLEMENTED else "prepare_weights" if not info else "gpu_unavailable"
            reason=REASONS.get(reason_code)
            models.append({**e,"ready":ready,"reason":reason,"reason_code":reason_code,...})
```
For `setup_needed`, pass `details="; ".join(missing)`. For `judge_not_ready`, use `ArenaError("judge_not_ready",ready["judge"]["reason"],reason=ready["judge"]["reason"])`.

- [ ] **Step 5: Add the catalog entries**

Add `errors` and `readiness` objects to `locales/en/ui.json` with every row from the tables above. For pass-through messages, use `"judge_not_ready": "{{reason}}"` and `"runtime_changed"` with the verbatim text from controller.py:310. Add Hungarian translations to `locales/hu/ui.json`, for example:
```json
"errors": {
  "duplicate_entrants": "Ismétlődő résztvevők",
  "unknown_entrant": "Ismeretlen résztvevő",
  "idempotency_conflict": "Az idempotencia-kulcsot más beállításokkal használták újra",
  "gpu_busy_run": "Egy másik futtatás használja a GPU-t. Állítsd le, vagy várd meg, amíg befejeződik.",
  "gpu_busy_process": "Egy másik Arena-folyamat használja a GPU-t. Várd meg, amíg a futtatása befejeződik.",
  "setup_needed": "Beállítás szükséges: {{details}}",
  "judge_not_ready": "{{reason}}",
  "run_not_found": "A futtatás nem található",
  "another_run_active": "Egy másik futtatás aktív",
  "run_complete": "A futtatás már befejeződött",
  "case_manifest_modified": "A rögzített esetlista módosult",
  "demo_needs_sources": "A Demóhoz a rögzített nyilvános JevBench-források kellenek. Előbb használd a Beállításban a „Kijelöltek előkészítése” gombot.",
  "suite_not_prepared": "A teljes tesztcsomag nincs előkészítve: {{missing}}",
  "duplicate_case_ids": "Ismétlődő esetazonosítók a tesztcsomagban",
  "abcd_case_not_found": "Az ABCD-eset nem található",
  "outcome_needs_model": "Az eredmény szerinti szűréshez válassz modellt",
  "case_not_found": "Az eset nem található",
  "invalid_event_cursor": "Érvénytelen eseménykurzor",
  "choose_entrants": "Válassz regisztrált résztvevőket",
  "preparation_running": "Az előkészítés már fut",
  "wait_for_active_run": "A futtatókörnyezet fájljainak módosítása előtt várd meg az aktív futtatást",
  "unknown_language": "Ismeretlen nyelv: {{language}}",
  "report_read_only": "Ez a mentett jelentés csak olvasható. Modellek futtatásához indítsd el a Jev Arenát."
},
"readiness": {
  "add_typesafe_key": "Add meg a TypeSafe-kulcsodat",
  "native_pending": "A natív integráció még hiányzik",
  "prepare_weights": "Készítsd elő a modellsúlyokat",
  "gpu_unavailable": "A GPU-worker nem érhető el"
}
```
Translate `runtime_changed` from the verbatim English as well.

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `uv run pytest -q`
Expected: the whole suite passes. The existing tests that compare English error text keep passing because the messages are unchanged.

- [ ] **Step 7: Commit**

```bash
git add arena tests/test_i18n_errors.py locales
git commit -m "feat(i18n): stable error and readiness codes for translated messages"
```

---

### Task 4: Catalog checker and `new-language` CLI

**Files:**
- Create: `arena/i18n/check.py`, `arena/i18n/__main__.py`
- Modify: `.github/workflows/verify.yml` (add the check step after pytest)
- Test: `tests/test_i18n_check.py`

**Interfaces:**
- Consumes: `locales.discover`, `load_catalog`, `flatten`, `base_key`, `completeness`
- Produces:
  - `check.Issue = NamedTuple(level: Literal["error","warning"], lang: str, file: str, key: str, message: str)`
  - `check.check(lang: str | None = None, root: Path = LOCALES) -> list[Issue]`
  - `check.new_language(code: str, name: str, native: str, root: Path = LOCALES) -> Path`
  - CLI: `uv run python -m arena.i18n check [--lang L]` exits 1 on any error. `uv run python -m arena.i18n new-language <code> --name <English name> --native <native name>`
- Rules:
  - **error**: a key not in `en`; `{{placeholder}}` sets that differ from the `en` value; a value that is not a string; `locale.json` missing any of `code,name,nativeName,status,review,dir`; `status` not in `complete|beta`; `code` not equal to the directory name; a target that has some forms of a plural group but no `_other`.
  - **warning**: a missing or empty key (the `en` fallback is used at runtime).
  - Summary lines: `<lang> ui.json: 97.3% complete (12 missing)`.

- [ ] **Step 1: Write the failing tests**

`tests/test_i18n_check.py`:
```python
import json
from arena.i18n import check

META = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}

def write(root, code, ui, meta=None):
    d = root / code; d.mkdir(parents=True, exist_ok=True)
    (d / "locale.json").write_text(json.dumps({"code": code, **(META if meta is None else meta)}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps(ui), encoding="utf-8")

def levels(issues): return sorted((i.level, i.key) for i in issues)

def test_clean_locale_has_no_issues(tmp_path):
    write(tmp_path, "en", {"a": "Hi {{name}}"}); write(tmp_path, "xx", {"a": "Szia {{name}}"})
    assert check.check("xx", tmp_path) == []

def test_extra_key_and_placeholder_mismatch_are_errors(tmp_path):
    write(tmp_path, "en", {"a": "Hi {{name}}"}); write(tmp_path, "xx", {"a": "Szia {{nev}}", "z": "x"})
    assert levels(check.check("xx", tmp_path)) == [("error", "a"), ("error", "z")]

def test_missing_and_empty_are_warnings(tmp_path):
    write(tmp_path, "en", {"a": "A", "b": "B"}); write(tmp_path, "xx", {"a": ""})
    assert levels(check.check("xx", tmp_path)) == [("warning", "a"), ("warning", "b")]

def test_plural_group_needs_other(tmp_path):
    write(tmp_path, "en", {"n_one": "{{count}} x", "n_other": "{{count}} xs"})
    write(tmp_path, "xx", {"n_one": "{{count}} y"})
    assert ("error", "n") in levels(check.check("xx", tmp_path))

def test_bad_metadata_is_error(tmp_path):
    write(tmp_path, "en", {"a": "A"}); write(tmp_path, "xx", {"a": "A"}, meta={**META, "status": "done"})
    assert any(i.level == "error" and i.file == "locale.json" for i in check.check("xx", tmp_path))

def test_new_language_scaffold_is_valid_and_empty(tmp_path):
    write(tmp_path, "en", {"g": {"a": "A {{n}}"}})
    check.new_language("xx", "Example", "Exemplum", tmp_path)
    assert json.loads((tmp_path / "xx" / "ui.json").read_text(encoding="utf-8")) == {"g": {"a": ""}}
    assert json.loads((tmp_path / "xx" / "locale.json").read_text(encoding="utf-8"))["status"] == "beta"
    assert all(i.level == "warning" for i in check.check("xx", tmp_path))

def test_repo_locales_have_no_errors():
    assert [i for i in check.check() if i.level == "error"] == []
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_i18n_check.py -v`
Expected: FAIL with `ImportError: cannot import name 'check'`.

- [ ] **Step 3: Implement `check.py`**

```python
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
```
The plural rule needs `_other` only when other forms exist; the per-key warning loop handles a group that is missing entirely.

- [ ] **Step 4: Implement the CLI**

`arena/i18n/__main__.py`:
```python
import argparse
import sys
from arena.i18n import check

def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m arena.i18n", description="Jev Arena translation tools")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="Validate locale catalogs against en")
    c.add_argument("--lang")
    c.add_argument("--quiet", action="store_true", help="Print errors only")
    n = sub.add_parser("new-language", help="Scaffold locales/<code>/ from en")
    n.add_argument("code"); n.add_argument("--name", required=True); n.add_argument("--native", required=True)
    args = parser.parse_args(argv)
    if args.command == "new-language":
        print(f"Created {check.new_language(args.code, args.name, args.native)}. Next: translate ui.json, then run check.")
        return 0
    issues = check.check(args.lang)
    for i in issues:
        if i.level == "error" or not args.quiet: print(f"{i.level.upper():7} {i.lang}/{i.file} {i.key}: {i.message}")
    for line in check.summary(args.lang): print(line)
    return 1 if any(i.level == "error" for i in issues) else 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Add the check to CI**

In `.github/workflows/verify.yml`, after `- run: uv run pytest -q`, add:
```yaml
      - run: uv run python -m arena.i18n check --quiet
```

- [ ] **Step 6: Run the tests and the CLI**

Run: `uv run pytest tests/test_i18n_check.py -v && uv run python -m arena.i18n check --quiet`
Expected: tests pass. The CLI prints `hu ui.json: …% complete` and exits 0.

- [ ] **Step 7: Commit**

```bash
git add arena/i18n tests/test_i18n_check.py .github/workflows/verify.yml
git commit -m "feat(i18n): catalog checker and new-language scaffold"
```

---

### Task 5: Frontend i18n runtime and formatters

**Files:**
- Modify: `package.json` (add dependencies), `package-lock.json`
- Create: `apps/web/src/format.ts`, `apps/web/src/i18n.ts`, `apps/web/src/labels.ts`
- Modify: `apps/web/src/types.ts` (add `export type LocaleInfo = { code: string; name: string; nativeName: string; status: "complete" | "beta"; completeness: number }`)
- Modify: `apps/web/src/vite-env.d.ts` (only if `import.meta.glob` types are missing; `vite/client` provides them)
- Test: `apps/web/tests/format.test.mjs`, `apps/web/tests/i18n.test.mjs`

**Interfaces:**
- Produces (`format.ts`, pure; every function takes `locale` first; `null`/`undefined` → `"—"` unless noted):
  - `number(locale: string, v: number|null|undefined, maxDigits = 0): string`
  - `fixed(locale: string, v: number|null|undefined, digits: number): string` (exact fraction digits; replaces `toFixed`)
  - `percent(locale: string, v: number|null|undefined, digits = 1): string` (input is a 0..1 ratio)
  - `points(locale: string, v: number|null|undefined, digits = 1): string` (percentage points with a sign: `+1.2 pp` / `+1,2 sz.p.`; the unit comes from the caller's `t("common.pp")`, see `ui.json`)
  - `duration(locale: string, ms: number|null|undefined): string` (`<1 ms`, `12 ms`, `1.25 s`; the number is localized, the SI symbol is fixed)
  - `shortDate(locale: string, epochSeconds: number): string` (month short + day)
- Produces (`i18n.ts`):
  - `export const i18n` (i18next instance)
  - `export function initI18n(language: string): Promise<void>`
  - `export function setLanguage(code: string): Promise<void>` (changes i18next and `document.documentElement.lang`; does **not** call the API)
  - `export function useFormat(): { number, fixed, percent, points, duration, shortDate }`, each bound to the active language
  - `export { useTranslation } from "react-i18next"`
  - `export const bundledLocales: LocaleInfo[]` (from the bundled `locale.json` files; `completeness: 1`)
- Produces (`labels.ts`):
  - `slug(name: string): string` (lowercase; runs of non-`[a-z0-9]` become `-`; trimmed)
  - `packLabel(t: TFunction, name: string): string` → `t("packs."+slug(name), {defaultValue: name})`
  - `familyLabel(t: TFunction, name: string): string` → `t("families."+slug(name), {defaultValue: name})`

- [ ] **Step 1: Install the dependencies**

```bash
npm install i18next@^25 react-i18next@^15
npm install -D i18next-parser@^9 eslint@^9 eslint-plugin-i18next@^6 typescript-eslint@^8
```
Expected: `package.json` lists them and `npm run build` still succeeds.

- [ ] **Step 2: Write the failing formatter tests**

`apps/web/tests/format.test.mjs`:
```js
import assert from 'node:assert/strict';
import test from 'node:test';
import { number, fixed, percent, duration, shortDate, points } from '../src/format.ts';

// Normalize ICU's non-breaking spaces and Unicode minus for stable comparisons.
const nb = s => s.replace(/[\u00a0\u202f]/g, ' ').replace(/\u2212/g, '-');

test('English formatting matches the previous hand-built output', () => {
  assert.equal(percent('en', 0.1234), '12.3%');
  assert.equal(percent('en', null), '—');
  assert.equal(number('en', 7671), '7,671');
  assert.equal(fixed('en', 0.12345, 4), '0.1235');
  assert.equal(duration('en', 0.4), '<1 ms');
  assert.equal(duration('en', 12.3), '12 ms');
  assert.equal(duration('en', 1250), '1.25 s');
  assert.equal(points('en', 0.012), '+1.2');
});

test('Hungarian uses comma decimals and space grouping', () => {
  assert.equal(nb(percent('hu', 0.1234)), '12,3%');
  assert.equal(nb(number('hu', 12345)), '12 345');
  assert.equal(number('hu', 7671), '7671'); // CLDR: Hungarian does not group 4-digit numbers
  assert.equal(nb(duration('hu', 1250)), '1,25 s');
  assert.equal(nb(points('hu', -0.012)), '-1,2');
  assert.match(shortDate('hu', 1759579200), /okt\. 4\./);
});
```

- [ ] **Step 3: Run the test and confirm it fails**

Run: `node --experimental-strip-types --test apps/web/tests/format.test.mjs`
Expected: FAIL (cannot find module `format.ts`).

- [ ] **Step 4: Implement `format.ts`**

```ts
type N = number | null | undefined;
const DASH = "—";
const nf = (locale: string, o: Intl.NumberFormatOptions) => new Intl.NumberFormat(locale, o);

export const number = (locale: string, v: N, maxDigits = 0) =>
  v == null ? DASH : nf(locale, { maximumFractionDigits: maxDigits }).format(v);

export const fixed = (locale: string, v: N, digits: number) =>
  v == null ? DASH : nf(locale, { minimumFractionDigits: digits, maximumFractionDigits: digits, useGrouping: false }).format(v);

export const percent = (locale: string, v: N, digits = 1) =>
  v == null ? DASH : nf(locale, { style: "percent", minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v);

/** Signed percentage-point delta without unit; callers append t("common.pp"). */
export const points = (locale: string, v: N, digits = 1) =>
  v == null ? DASH : nf(locale, { signDisplay: "exceptZero", minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v * 100);

/** SI symbols (ms, s) are language-neutral; only the number is localized. */
export const duration = (locale: string, ms: N) => {
  if (ms == null) return DASH;
  if (ms < 1) return "<1 ms";
  if (ms >= 1000) return `${fixed(locale, ms / 1000, 2)} s`;
  return `${number(locale, ms, ms < 10 ? 1 : 0)} ms`;
};

export const shortDate = (locale: string, epochSeconds: number) =>
  new Date(epochSeconds * 1000).toLocaleDateString(locale, { month: "short", day: "numeric" });
```
The previous UI printed `12ms` and `1.25s` without a space. The space before the SI symbol is an intended change, and it is the correct form in Hungarian.

- [ ] **Step 5: Run the formatter tests and confirm they pass**

Run: `node --experimental-strip-types --test apps/web/tests/format.test.mjs`
Expected: PASS.

- [ ] **Step 6: Write the failing i18n runtime test**

`apps/web/tests/i18n.test.mjs` (uses a fresh i18next instance with catalogs read from disk, so it runs in Node without Vite):
```js
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import i18next from 'i18next';
import { slug } from '../src/labels.ts';

const load = code => JSON.parse(readFileSync(new URL(`../../../locales/${code}/ui.json`, import.meta.url)));

test('Hungarian resolves keys, falls back to English for empty values, keeps placeholders', async () => {
  const i = i18next.createInstance();
  await i.init({ lng: 'hu', fallbackLng: 'en', returnEmptyString: false,
    resources: { en: { translation: { ...load('en'), probe: { empty: 'English' } } },
                 hu: { translation: { ...load('hu'), probe: { empty: '' } } } } });
  assert.equal(i.t('nav.results'), 'Eredmények');
  assert.equal(i.t('probe.empty'), 'English');
  assert.equal(i.t('shell.workspaceLabel', { appName: 'Jev Arena' }), 'Jev Arena munkaterület');
});

test('slug makes stable catalog keys from pack names', () => {
  assert.equal(slug('Arena Fresh'), 'arena-fresh');
  assert.equal(slug('JevBench public'), 'jevbench-public');
  assert.equal(slug('SST-2'), 'sst-2');
  assert.equal(slug('Sci/Tech'), 'sci-tech');
});
```

- [ ] **Step 7: Implement `labels.ts` and `i18n.ts`**

`apps/web/src/labels.ts`:
```ts
import type { TFunction } from "i18next";

export const slug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
export const packLabel = (t: TFunction, name: string) => t(`packs.${slug(name)}`, { defaultValue: name });
export const familyLabel = (t: TFunction, name: string) => t(`families.${slug(name)}`, { defaultValue: name });
```
`apps/web/src/i18n.ts`:
```ts
import i18next from "i18next";
import { initReactI18next, useTranslation } from "react-i18next";
import { useMemo } from "react";
import * as f from "./format";
import type { LocaleInfo } from "./types";

// Bundled at build time so the standalone report works offline.
const modules = import.meta.glob("/locales/*/ui.json", { eager: true, import: "default" }) as Record<string, object>;
const metas = import.meta.glob("/locales/*/locale.json", { eager: true, import: "default" }) as Record<string, Omit<LocaleInfo, "completeness">>;
const code = (path: string) => path.split("/")[2];
const resources = Object.fromEntries(Object.entries(modules).map(([path, translation]) => [code(path), { translation }]));
export const bundledLocales: LocaleInfo[] = Object.values(metas)
  .map(m => ({ code: m.code, name: m.name, nativeName: m.nativeName, status: m.status, completeness: 1 }))
  .sort((a, b) => Number(a.code !== "en") - Number(b.code !== "en") || a.code.localeCompare(b.code));
export const i18n = i18next;

export async function initI18n(language: string) {
  await i18next.use(initReactI18next).init({
    resources, lng: language, fallbackLng: "en", returnEmptyString: false,
    interpolation: { escapeValue: false }, // React escapes.
  });
  document.documentElement.lang = language;
}

export async function setLanguage(code: string) {
  await i18next.changeLanguage(code);
  document.documentElement.lang = code;
}

export function useFormat() {
  const { i18n: active } = useTranslation();
  const l = active.language;
  return useMemo(() => ({
    number: (v: number | null | undefined, d = 0) => f.number(l, v, d),
    fixed: (v: number | null | undefined, d: number) => f.fixed(l, v, d),
    percent: (v: number | null | undefined, d = 1) => f.percent(l, v, d),
    points: (v: number | null | undefined, d = 1) => f.points(l, v, d),
    duration: (v: number | null | undefined) => f.duration(l, v),
    shortDate: (s: number) => f.shortDate(l, s),
  }), [l]);
}

export { useTranslation };
```

- [ ] **Step 8: Run all node tests**

Run: `node --experimental-strip-types --test apps/web/tests/*.test.mjs`
Expected: PASS, including the existing navigation tests.

- [ ] **Step 9: Commit**

```bash
git add package.json package-lock.json apps/web/src/format.ts apps/web/src/i18n.ts apps/web/src/labels.ts apps/web/tests
git commit -m "feat(i18n): i18next runtime, Intl formatters and label helpers"
```

---

### Task 6: Boot, language switcher, shell and navigation

**Files:**
- Create: `apps/web/src/LanguageSwitcher.tsx`, `apps/web/src/EnglishOnly.tsx`
- Modify: `apps/web/src/main.tsx:78-160` (offline type, `api()`, boot), `:380-420` (AppShell props)
- Modify: `apps/shared/AppShell.tsx` (translatable strings, `headerExtra` slot)
- Modify: `apps/web/src/navigation.ts:1-5`, `apps/web/src/ViewHistory.tsx:69`
- Modify: `apps/web/src/styles.css` (switcher styles)
- Test: `apps/web/tests/navigation.test.mjs` (update), manual browser check

**Interfaces:**
- Consumes: `initI18n`, `setLanguage`, `useTranslation`, `bundledLocales` (Task 5); `GET/POST /api/i18n` (Task 2); `errors.*` and `readiness.*` keys (Task 3)
- Produces:
  - `navigation.ts`: `export const pageKeys: Record<string, string>` (page id → `"nav.<id>"`). `pageNames` is removed.
  - `AppShell` props: `labels: ShellLabels` (an object with the translated `shell.*` strings) and `headerExtra?: ReactNode`
  - `LanguageSwitcher` with props `{ locales: LocaleInfo[]; language: string; onChange(code: string): void }`, where `type LocaleInfo = { code: string; name: string; nativeName: string; status: "complete"|"beta"; completeness: number }` is exported from `types.ts`
  - `EnglishOnly`: `<EnglishOnly>{children}</EnglishOnly>` shows `shell.englishOnly` above the children when the language is not `en`
  - `api()` errors: `class ApiError extends Error { code?: string; params?: Record<string, unknown> }`, plus `errorText(t, e)` in `main.tsx` that returns `t("errors."+code, {...params, defaultValue: message})`
  - Offline report: `window.__ARENA_REPORT__.language?: string`, and `api("/i18n")` offline returns `{language: offline.language ?? "en", locales: bundledLocales}`

- [ ] **Step 1: Update the navigation test first**

In `apps/web/tests/navigation.test.mjs`, add:
```js
import { pageKeys } from '../src/navigation.ts';
test('every page id maps to a nav catalog key', () => {
  for (const [id, key] of Object.entries(pageKeys)) assert.equal(key, `nav.${id}`);
});
```
Run: `node --experimental-strip-types --test apps/web/tests/navigation.test.mjs`
Expected: FAIL (`pageKeys` is not exported).

- [ ] **Step 2: Replace `pageNames` with `pageKeys`**

`apps/web/src/navigation.ts:1-5`:
```ts
const pageIds = ["arena", "results", "cases", "abcd", "models", "takeaways", "sources", "chart", "replay", "run", "setup"] as const;
/** Page id → catalog key. Ids are stable history state; labels are translated. */
export const pageKeys: Record<string, string> = Object.fromEntries(pageIds.map(id => [id, `nav.${id}`]));
```
Replace every `pageNames` in this file with `pageKeys` (the `Object.hasOwn` checks only test membership). In `ViewHistory.tsx`, import `pageKeys` and `useTranslation`. Line 69 becomes:
```ts
backLabel: t(pageKeys[entry.previousPage || ""] ?? "nav.previousView") };
```
`ViewHistory.tsx` must get `t` through `useTranslation()` in the hook that builds this object.

- [ ] **Step 3: Make `AppShell` translatable**

Add to `apps/shared/AppShell.tsx`:
```ts
export type ShellLabels = {
  skipToContent: string; expandNavigation: string; collapseNavigation: string; presenter: string;
  exitPresenter: string; exitPresenterTitle: string; presenterTitle: string; workspace: string;
  localWorkspace: string; homeLabel: string; workspaceLabel: string; navigationLabel: string;
};
```
Add `labels: ShellLabels; headerExtra?: ReactNode;` to `AppShellProps`. Replace each literal with the matching label, for example `aria-label={labels.homeLabel}`, `{labels.skipToContent}`, `<span>WORKSPACE</span>` → `<span>{labels.workspace}</span>`. Render `{headerExtra}` as the first child of `.taia-header-actions`. `AppShell` stays free of i18next (it is a shared component). The caller passes strings in.

- [ ] **Step 4: Create the switcher and the English-only note**

`apps/web/src/LanguageSwitcher.tsx`:
```tsx
import { Languages } from "lucide-react";
import { useTranslation } from "./i18n";
import type { LocaleInfo } from "./types";

export function LanguageSwitcher({ locales, language, onChange }: { locales: LocaleInfo[]; language: string; onChange: (code: string) => void }) {
  const { t } = useTranslation();
  if (locales.length < 2) return null;
  return <label className="language-switcher" title={t("shell.language")}>
    <Languages size={16} aria-hidden="true" />
    <select aria-label={t("shell.language")} value={language} onChange={e => onChange(e.target.value)}>
      {locales.map(l => <option key={l.code} value={l.code}>{l.nativeName}{l.status === "beta" ? ` (${t("shell.beta")})` : ""}</option>)}
    </select>
  </label>;
}
```
`apps/web/src/EnglishOnly.tsx`:
```tsx
import type { ReactNode } from "react";
import { useTranslation } from "./i18n";

export function EnglishOnly({ children }: { children: ReactNode }) {
  const { t, i18n } = useTranslation();
  return <div lang="en">{i18n.language !== "en" && <p className="small muted english-only">{t("shell.englishOnly")}</p>}{children}</div>;
}
```
(`LocaleInfo` was added to `types.ts` in Task 5.) Append to `styles.css`:
```css
.language-switcher{display:inline-flex;align-items:center;gap:6px}
.language-switcher select{background:transparent;color:inherit;border:1px solid currentColor;border-radius:6px;padding:2px 6px;font:inherit}
.english-only{margin:0 0 8px}
```

- [ ] **Step 5: Boot and wire everything in `main.tsx`**

1. Extend the global declaration at line 78 with `language?: string` on `__ARENA_REPORT__`.
2. In `api()`:
   - Offline, `path === "/i18n"` returns `{ language: offline.language ?? "en", locales: bundledLocales }`. This works before i18next is initialized, because `bundledLocales` comes from `locale.json`, not from translations.
   - When `!r.ok`, throw `Object.assign(new Error(message), { code: data.code, params: data.params })`.
   - Replace the read-only message with `Object.assign(new Error("This saved report is read-only. Launch Jev Arena to run models."), { code: "report_read_only" })`.
3. Add `const errorText = (t: TFunction, e: unknown) => { const x = e as Error & { code?: string; params?: object }; return x.code ? t(`errors.${x.code}`, { ...x.params, defaultValue: x.message }) : x.message; };` and replace every `setError((e as Error).message)` with `setError(errorText(t, e))`.
4. Boot: replace the `createRoot(...).render(...)` at the end with:
```tsx
(async () => {
  const state = await api<{ language: string; locales: LocaleInfo[] }>("/i18n").catch(() => ({ language: "en", locales: [] }));
  await initI18n(state.language);
  createRoot(document.getElementById("root")!).render(/* existing tree unchanged */);
})();
```
5. In `App()`, load `/i18n` into state `locales`, and pass `AppShell` the following:
   - `labels` built from `t("shell.*")`
   - `navigation` labels as `t("nav.<id>")`
   - `appName="Jev Arena"` (a product name, not translated)
   - `description={t("shell.description")}` (add `"description": "Decision model lab"` / `"Döntési modell labor"`)
   - `headerExtra={<LanguageSwitcher locales={locales} language={i18n.language} onChange={changeLanguage} />}`, where:
```ts
async function changeLanguage(code: string) {
  if (!offline) await api("/i18n", { language: code });
  await setLanguage(code);
}
```
6. Translate the remaining strings in the `AppShell` element (status, sidebar footer, footer note) by adding `overview.*` keys.

The `api()` helper sends POST whenever `body` is set, which matches `POST /api/i18n`.

- [ ] **Step 6: Run the tests and the build**

Run: `node --experimental-strip-types --test apps/web/tests/*.test.mjs && npm run build && uv run python -m arena.i18n check --quiet`
Expected: all pass.

- [ ] **Step 7: Check in the browser**

Start the app with `bash start-arena.sh`, or run `uv run uvicorn arena.api:app --port 8787` together with `npm run dev`. Then:
- Open http://127.0.0.1:5173 and switch to Magyar. The sidebar shows "Áttekintés, Eredmények…", `<html lang="hu">` is set, and a reload keeps Hungarian because it is saved on the server.
- Switch back to English.

- [ ] **Step 8: Commit**

```bash
git add apps locales
git commit -m "feat(i18n): language switcher, translated shell and navigation, coded API errors"
```

---

### Task 7: Extract strings from `main.tsx` (App, Metric, Frontier, Empty)

**Files:**
- Modify: `apps/web/src/main.tsx:137-160` (formatters) and `:160-1150` (App, Metric, Frontier) and `:1812-1834` (Empty)
- Modify: `locales/en/ui.json`, `locales/hu/ui.json` (namespaces `overview`, `common`, `packs`, `families`)
- Create: `eslint.i18n.config.js`, `i18next-parser.config.js`; add npm scripts
- Test: `npm run i18n:lint`, `npm run i18n:extract`, the build

**Interfaces:**
- Consumes: `useTranslation`, `useFormat` (Task 5); `packLabel`, `familyLabel` (Task 5)
- Produces:
  - npm script `i18n:lint`: ESLint `i18next/no-literal-string` in `jsx-text-only` mode over `apps/web/src` and `apps/shared`; exits non-zero on untranslated JSX text
  - npm script `i18n:extract`: i18next-parser writes keys found in code into `locales/en/ui.json`, keeps existing values and reports unused keys
  - `main.tsx` module-level `pct`, `num`, `ms` are deleted; components call `useFormat()` instead

**Extraction procedure** (Tasks 7 to 11 all follow it):
1. Add `const { t } = useTranslation(); const fmt = useFormat();` at the top of every component that renders text.
2. Replace JSX text, `title`, `aria-label`, `placeholder` and `alt` literals, and string literals that reach the screen, with `t("<namespace>.<camelCaseKey>")`. Pick keys from the meaning, not the position (`overview.sharedQuestionAccuracy`, not `overview.text12`).
3. Put dynamic parts in placeholders: `` `${n} planned records` `` becomes `t("operations.plannedRecords", { count: n })` with `"plannedRecords_one": "{{count}} planned record"` and `"plannedRecords_other": "{{count}} planned records"`. Never build a sentence by joining translated pieces.
4. Inline markup inside a sentence (`<strong>`, links) uses `<Trans i18nKey="…" components={{ b: <strong/> }} />` with `"… <b>bold</b> …"` in the catalog.
5. Not translated: product and model names (Jev, Laya, Plumb…), metric acronyms that are code identifiers (F1, Brier, NLL, MRR, nDCG@10 stay as they are in both catalogs), run ids, data values coming from the API, and CSS class names.
6. Pack and family names that come from data go through `packLabel(t, name)` / `familyLabel(t, name)`. Add a `packs.<slug>` and `families.<slug>` entry for every name in `arena/suites.py:EXPECTED`, `arena/fresh.py:FAMILIES` and the families that the importers create (SST-2, AG News, BANKING77, XNLI, MASSIVE, SciFact, Warehouse, Tickets).
7. Formatting: `pct(x,d)` → `fmt.percent(x,d)`, `num(x,d)` → `fmt.number(x,d)`, `ms(x)` → `fmt.duration(x)`, `x.toFixed(d)` → `fmt.fixed(x,d)`, `toLocaleDateString(undefined,{month:"short",day:"numeric"})` → `fmt.shortDate(seconds)`.
8. `label(s)` (line 156, which turns `snake_case` status values into words) becomes `t("status."+s, { defaultValue: label(s) })`. Add `status.*` keys for every run status in `arena/controller.py:TERMINAL` and the store: `queued`, `running`, `complete`, `cancelled`, `failed`, `interrupted`.
9. Add each new English key to `en/ui.json` and its Hungarian translation to `hu/ui.json` in the same commit, using the glossary below.

**Hungarian glossary** (use these consistently; record any additions in `docs/i18n/glossary-hu.md`, created in Task 12):

| English | Hungarian |
|---|---|
| run (noun) | futtatás |
| test | teszt |
| case / question | eset / kérdés |
| model / entrant | modell / résztvevő |
| accuracy | pontosság |
| shared questions | közös kérdések |
| response time / latency | válaszidő / késleltetés |
| setup | beállítás |
| prepare | előkészítés |
| results | eredmények |
| workflow replay | munkafolyamat-visszajátszás |
| evidence | bizonyíték |
| report | jelentés |
| judge (audit) | bíráló |
| label | címke |
| pack / suite | csomag / tesztcsomag |
| support conversation | ügyfélszolgálati beszélgetés |
| percentage points (pp) | százalékpont (sz.p.) |
| benchmark | benchmark |
| checkpoint | ellenőrzőpont |

Use the informal second person singular (`te`) form in Hungarian UI text ("Válassz", "Indítsd el"), as already used in Task 3.

- [ ] **Step 1: Add the lint and extract tooling**

`eslint.i18n.config.js`:
```js
import tseslint from "typescript-eslint";
import i18next from "eslint-plugin-i18next";

export default [
  { files: ["apps/web/src/**/*.tsx", "apps/shared/**/*.tsx"],
    languageOptions: { parser: tseslint.parser },
    plugins: { i18next },
    rules: { "i18next/no-literal-string": ["error", { mode: "jsx-text-only",
      "jsx-attributes": { include: ["title", "aria-label", "placeholder", "alt"] },
      words: { exclude: ["Jev Arena", "Jev", "—", "·", "/", "%", "\\s*[→←×+]\\s*", "[0-9.,:]+", "F1", "MRR", "nDCG@10", "N/A"] } }] } },
];
```
`i18next-parser.config.js`:
```js
export default {
  locales: ["en"],
  input: ["apps/web/src/**/*.{ts,tsx}", "apps/shared/**/*.tsx"],
  output: "locales/$LOCALE/ui.json",
  keySeparator: ".",
  namespaceSeparator: false,
  keepRemoved: [/^errors\./, /^readiness\./, /^packs\./, /^families\./, /^status\./, /^nav\./],
  createOldCatalogs: false,
  failOnUpdate: false,
  sort: true,
  indentation: 2,
  defaultValue: (locale, ns, key, value) => value ?? "",
};
```
In `package.json` `scripts`, add:
```json
"i18n:lint": "eslint --config eslint.i18n.config.js apps/web/src apps/shared",
"i18n:extract": "i18next-parser --config i18next-parser.config.js"
```
Run `npm run i18n:lint`. Expected: many errors at this point, which is the to-do list for Tasks 7 to 11. Record the count in the commit message.

**`keepRemoved` caveat:** keys used dynamically (`errors.${code}`, `packs.${slug}`, `status.${s}`, `nav.${id}` through `pageKeys`) can't be detected by the parser. The patterns above protect them. Any new dynamic key family must be added here.

- [ ] **Step 2: Extract the App, Metric, Frontier and Empty components**

Follow the extraction procedure for `main.tsx` lines 137-1150 and 1812-1834. Delete the module-level `pct`, `num` and `ms` (lines 137-150) once nothing uses them. Keep `label` as the fallback described in procedure item 8.

- [ ] **Step 3: Run lint for this file region**

Run: `npx eslint --config eslint.i18n.config.js apps/web/src/main.tsx 2>&1 | awk -F: '$2<1150 || $2>1811'`
Expected: no remaining errors on lines 1-1150 or 1812-1834. Errors in `Results`, `Replay` and `Setup` remain for Task 8.

- [ ] **Step 4: Check catalogs and build**

Run: `uv run python -m arena.i18n check --quiet && npm run build && node --experimental-strip-types --test apps/web/tests/*.test.mjs`
Expected: no check errors; build OK; tests pass.

- [ ] **Step 5: Spot-check in the browser**

With the app running, check the Overview page in English. The text must match the previous wording. The only differences allowed are number spacing from `Intl` (for example `12 ms`). Then check Magyar: no English remains outside names, acronyms and data.

- [ ] **Step 6: Commit**

```bash
git add apps locales package.json package-lock.json eslint.i18n.config.js i18next-parser.config.js
git commit -m "feat(i18n): extract overview strings; add i18n lint and extract tooling"
```

---

### Task 8: Extract strings from `main.tsx` (Results, Replay, Setup)

**Files:**
- Modify: `apps/web/src/main.tsx:1150-1811`
- Modify: `locales/en/ui.json`, `locales/hu/ui.json` (namespaces `results`, `replay`, `setup`, `readiness`)
- Test: lint, check, build

**Interfaces:**
- Consumes: the extraction procedure and glossary (Task 7)
- Produces: in `Setup`, a model that isn't ready shows `t("readiness."+m.reason_code, { defaultValue: m.reason })`. The judge-readiness text from `arena/judge.py` is shown inside `<EnglishOnly>`, because it comes from a separate preflight module whose text Phase 1 doesn't translate.

- [ ] **Step 1: Extract the strings**

Follow the procedure for lines 1150-1811. Metric table labels at lines 1303-1307 ("Macro F1", "Binary Brier", "Multiclass Brier", "Negative log loss", "Expected-score MAE") become `results.metrics.*` keys; the Hungarian keeps the acronyms ("Makro F1", "Bináris Brier", "Többosztályos Brier", "Negatív log-likelihood", "Várható pontszám MAE"). The `toFixed` calls on those lines become `fmt.fixed(…)`. The clock at line 1491 becomes `fmt.fixed(clock / 1000, 1)`.

- [ ] **Step 2: Lint, check and build**

Run: `npx eslint --config eslint.i18n.config.js apps/web/src/main.tsx && uv run python -m arena.i18n check --quiet && npm run build`
Expected: no lint errors in `main.tsx`; check and build pass.

- [ ] **Step 3: Browser check**

Check Results, Run a new test and Setup in both languages. In Setup, temporarily set a fake model to not ready if needed to see a `readiness.*` message.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/main.tsx locales
git commit -m "feat(i18n): extract results, replay and setup strings"
```

---

### Task 9: Extract strings from `Operations.tsx`

**Files:**
- Modify: `apps/web/src/Operations.tsx` (726 lines; local formatters at lines 16-18)
- Modify: `locales/*/ui.json` (namespace `operations`)

**Interfaces:**
- Consumes: the extraction procedure and glossary (Task 7)
- Produces: the local `seconds`/`pct` helpers at lines 16-18 are deleted. The `N/A` fallback becomes `t("common.notApplicable")`. Percentage-point deltas use `` `${fmt.points(c.delta)} ${t("common.pp")}` `` with `"common.pp": "pp"` / `"sz.p."`. Confidence intervals use `t("operations.ciRange", { low: fmt.fixed(c.ci[0]*100,1), high: fmt.fixed(c.ci[1]*100,1) })` with `"({{low}} to {{high}})"` / `"({{low}}–{{high}})"`.

- [ ] **Step 1: Extract the strings** following the procedure. Warehouse direction labels used as display text (north/east/…) are translated through `operations.directions.*`. The values compared in code stay unchanged.
- [ ] **Step 2: Lint, check and build**

Run: `npx eslint --config eslint.i18n.config.js apps/web/src/Operations.tsx && uv run python -m arena.i18n check --quiet && npm run build`
Expected: clean.

- [ ] **Step 3: Browser check** of the operations panels and a workflow replay in both languages.
- [ ] **Step 4: Commit**

```bash
git add apps/web/src/Operations.tsx locales
git commit -m "feat(i18n): extract operations and workflow replay strings"
```

---

### Task 10: Extract strings from `Explore.tsx`, `ABCDCases.tsx` and `ViewHistory.tsx`

**Files:**
- Modify: `apps/web/src/Explore.tsx` (local formatters at lines 21-22; strings at 63, 74, 106, 116, …), `apps/web/src/ABCDCases.tsx`, `apps/web/src/ViewHistory.tsx`
- Modify: `locales/*/ui.json` (namespaces `explore`, `abcd`)

**Interfaces:**
- Consumes: the extraction procedure, glossary, `packLabel`, `familyLabel` (Task 7)
- Produces: `Explore.tsx` `title(pack, family)` uses `packLabel`/`familyLabel`. `"{n} matching questions"` uses the plural keys `explore.matchingQuestions_one/_other`. Case text, state, model answers and conversation transcripts are data and are **not** translated.

- [ ] **Step 1: Extract the strings** following the procedure. In Hungarian, `matchingQuestions_one` is "{{count}} találat" and `_other` is "{{count}} találat" (Hungarian nouns stay singular after numbers; both forms are needed for the check).
- [ ] **Step 2: Lint, check and build**

Run: `npx eslint --config eslint.i18n.config.js apps/web/src/Explore.tsx apps/web/src/ABCDCases.tsx apps/web/src/ViewHistory.tsx && uv run python -m arena.i18n check --quiet && npm run build`
Expected: clean.

- [ ] **Step 3: Browser check** of the Case explorer and Support conversations in both languages.
- [ ] **Step 4: Commit**

```bash
git add apps/web/src locales
git commit -m "feat(i18n): extract case explorer and ABCD case strings"
```

---

### Task 11: Extract strings from `Guide.tsx`; wrap long prose in `EnglishOnly`

**Files:**
- Modify: `apps/web/src/Guide.tsx` (85 dense lines; local `pct` at line 6; `sources` table at lines 28-36; `taskNames` at line 68)
- Modify: `locales/*/ui.json` (namespace `guide`)

**Interfaces:**
- Consumes: `EnglishOnly` (Task 6), the extraction procedure (Task 7)
- Produces: headings, table headers, button labels, short labels and `taskNames` are translated. Paragraph-length explanatory prose, and prose read from `docs/evidence/*.json` (`model-guide.json` notes/kind/context, `builder-task-breakdown.json`, `abcd-dashboard-data.json`, `video-task-analysis.json`, `video-findings.json`), stays English inside `<EnglishOnly>`, as the spec's option A requires.

**Rule for "long prose":** a JSX text block of more than one sentence, or any text that comes from `docs/evidence/*.json`. Everything else is translated.

- [ ] **Step 1: Extract the short strings and wrap the prose blocks.** The lint rule flags the prose blocks inside `<EnglishOnly>` too. Silence each wrapped block with `{/* eslint-disable-next-line i18next/no-literal-string -- English-only prose (spec option A) */}`, or move its text into a local `const` declared outside JSX, which `jsx-text-only` mode doesn't check. Prefer the `const`.
- [ ] **Step 2: Lint, check and build**

Run: `npm run i18n:lint && uv run python -m arena.i18n check --quiet && npm run build`
Expected: **the whole project lint passes** (this is the last extraction task).

- [ ] **Step 3: Browser check** of What we learned, Model guide and Tests & scoring in Magyar. Headings and labels are Hungarian, and the prose blocks show the "csak angolul érhető el" note.
- [ ] **Step 4: Commit**

```bash
git add apps/web/src/Guide.tsx locales
git commit -m "feat(i18n): extract guide labels; mark long prose English-only"
```

---

### Task 12: Contributor docs, README and CI lint

**Files:**
- Create: `docs/i18n/CONTRIBUTING-TRANSLATIONS.md`, `docs/i18n/ARCHITECTURE.md`, `docs/i18n/glossary-hu.md`
- Modify: `README.md` (add a "Languages" section after "Reproduce and develop"), `.github/workflows/verify.yml` (add `npm run i18n:lint` after `npm ci`)
- Test: `uv run python -m scripts.check_publication` (it checks markdown links)

**Interfaces:**
- Consumes: every command from Tasks 4 and 7
- Produces: documentation. Phases 2 and 3 append sections to these same files.

- [ ] **Step 1: Write `docs/i18n/CONTRIBUTING-TRANSLATIONS.md`**

Required sections and content:
1. **Overview.** What a locale contains in Phase 1 (`locale.json`, `ui.json`). Note that report text, prompts and dataset mapping arrive in later phases.
2. **Add a new language.** The exact commands:
```bash
uv run python -m arena.i18n new-language pl --name Polish --native Polski
# translate locales/pl/ui.json (empty strings fall back to English)
uv run python -m arena.i18n check --lang pl
npm run build && npm run dev
```
3. **Catalog rules.** Keep keys and `{{placeholders}}` unchanged; plurals use `_one`/`_other` (plus `_few`/`_many` etc. if the language needs them according to CLDR, which `Intl.PluralRules` follows); `<b>…</b>` tags in `Trans` strings must be preserved; don't translate product and model names or the metric acronyms listed in the glossary.
4. **beta vs complete.** `complete` requires `check` with zero warnings and a native-speaker review; set `review` to the reviewer's name or handle.
5. **Adding UI strings as a developer.** Use `t()`; run `npm run i18n:extract` to add new keys to `en/ui.json`; run `npm run i18n:lint`; add the key to other locales or leave it to fall back.
6. **Glossaries.** Each language may keep `docs/i18n/glossary-<code>.md`, with Hungarian as the example.
7. **Using translation platforms.** The `ui.json` files are i18next JSON v4 and can be imported directly into Weblate or Crowdin. Keep `en` as the source file.

- [ ] **Step 2: Write `docs/i18n/ARCHITECTURE.md`**

Describe the following, each with file paths: the locale bundle layout; the global setting and `/api/i18n`; the boot sequence (fetch `/i18n` → `initI18n` → render); build-time bundling with `import.meta.glob`; the offline report behaviour; `format.ts`; coded errors (`ArenaError`, `ArenaHTTPError`, `errors.*`, `readiness.*`); dynamic key families protected in the extract config; `EnglishOnly`. End with a "Later phases" note linking the spec.

- [ ] **Step 3: Write `docs/i18n/glossary-hu.md`** with the glossary table from Task 7, plus the informal `te` style rule, plus any terms added during Tasks 7 to 11.

- [ ] **Step 4: README section**

```markdown
## Languages

The interface is available in English and Hungarian (beta). Choose the language in the header; the choice is saved in `.arena/settings.json`. To add a language, see [Contributing translations] (docs/i18n/CONTRIBUTING-TRANSLATIONS.md).
```

- [ ] **Step 5: CI**

In `.github/workflows/verify.yml`, after `- run: npm ci`, add `- run: npm run i18n:lint`.

- [ ] **Step 6: Full verification**

Run:
```bash
uv run python -m scripts.check_publication
uv run pytest -q
uv run python -m arena.i18n check --quiet
npm run i18n:lint
node --experimental-strip-types --test apps/web/tests/*.test.mjs
npm run build
```
Expected: everything passes. If `check_publication` rejects new tracked paths (for example `locales/` or `docs/superpowers/`), read `scripts/check_publication.py` and add the paths to its allow-list.

- [ ] **Step 7: Align the spec and commit**

In `docs/superpowers/specs/2026-10-04-i18n-design.md`, CLI table: change the `extract` row to `npm run i18n:extract` (i18next-parser) plus `npm run i18n:lint` (literal-string lint). They are Node tools, so they live in npm scripts and not in the Python CLI.

```bash
git add docs/i18n docs/superpowers/specs README.md .github/workflows/verify.yml scripts/check_publication.py
git commit -m "docs(i18n): contributor guide, architecture, Hungarian glossary; lint in CI"
```

---

## Phase boundaries

- **Phase 2 (reports)** reuses `locales/*/report.json` (added to `check.CATALOGS`), `window.__ARENA_REPORT__.language`, and the bundled catalogs in the standalone report.
- **Phase 3 (data)** adds `prompts.yaml`, `datasets.yaml`, language-aware suites, and the translation engines and CLI commands.

Separate plans will be written for each once Phase 1 is merged.
