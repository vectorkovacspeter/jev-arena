# i18n architecture

## Locale bundles

`locales/<code>/locale.json` and `locales/<code>/ui.json` (`en` is the source). `arena/i18n/locales.py` discovers them (`discover()`, `available()`), computes completeness (a plural group counts once, translated when its `_other` form is) and skips locales that are unreadable or whose `code` differs from the directory name. `arena/i18n/check.py` validates catalogs and scaffolds new ones; `arena/i18n/__main__.py` is the CLI (`check`, `new-language`). In Phase 1 `check` covers `locale.json` and `ui.json` only. Run Python commands with `uv run --frozen` so `uv.lock` is never rewritten. Locale codes must match `^[a-z]{2,3}(-[A-Z]{2})?$`; unreadable catalogs are reported as check errors and count as 0% complete instead of breaking the API.

## Global language setting and API

The language is global, not per user. `arena/i18n/settings.py` stores `{"language": "<code>"}` in `<ARENA_DATA_DIR>/settings.json` (default `.arena/settings.json`); `get_language()` falls back to `en` for unknown codes.

- `GET /api/i18n` returns `{language, locales}` (each locale: code, name, nativeName, status, completeness).
- `POST /api/i18n` with `{"language": "<code>"}` sets it. It is a POST (not PUT) because the token and origin middleware and the frontend `api()` helper handle POST mutations.

## Boot sequence

`apps/web/src/main.tsx`: fetch `/i18n`, call `initI18n(state.language)` (`apps/web/src/i18n.ts`), then render. A failed fetch falls back to `en`. `initI18n` is idempotent (a second call only changes the language) and sets `document.documentElement.lang`. The header `LanguageSwitcher.tsx` POSTs the choice and calls `setLanguage`.

## Build-time bundling

`i18n.ts` uses `import.meta.glob("/locales/*/ui.json")` and `.../locale.json` (eager), so every catalog is compiled into the bundle. i18next runs with `fallbackLng: "en"` and `returnEmptyString: false`, so empty strings fall back to English. A new language needs a rebuild (`npm run build`) to show up.

## Offline reports

A saved report embeds `window.__ARENA_REPORT__`. When present, the app does not call the API: `/i18n` is answered from the embedded `language` (default `en`) and `bundledLocales`, and mutations throw a read-only error. The report therefore works offline with all bundled catalogs.

## Formatting

`apps/web/src/format.ts` wraps `Intl` (`number`, `fixed`, `percent`, `points`, `duration`, `shortDate`); `safeLocale` guards against invalid language tags. Components get them from `useFormat()`. Percentage points are formatted with `fmt.points` followed by `t("common.pp")`.

## Coded errors

`arena/i18n/errors.py` defines `ArenaError` (a `ValueError`) and `ArenaHTTPError`. Both keep the English message and add a stable `code` and `params`; the API returns `{detail, code, params}`. In the UI `errorText` (`apps/web/src/labels.ts`) translates `errors.<code>` with the params and falls back to `detail`.

- Readiness reasons carry a `reason_code`, translated as `readiness.<code>`. `setup_needed` carries `params.models[{name, reason_code}]`.
- Other label helpers in `labels.ts`: `slug`, `packLabel` (`packs.<slug>`), `familyLabel` (`families.<slug>`).

## Dynamic key families

Keys assembled at runtime (`errors.*`, `readiness.*`, `packs.*`, `families.*`, `status.*`, `nav.*` via `pageKeys` in `navigation.ts`, `results.verdicts`, `operations.{directions,queues,topics}`, `explore.{types,errors}`, `abcd.{errors,conditions}`, `setup.testData.sources`) are invisible to `i18next-parser`. `i18next-parser.config.js` protects them with `keepRemoved` patterns built from the `dynamic` list. The parser tests `translation:<key>` (namespace separator `:`), which is why the patterns start with `^translation:`. Add every new family there.

## English-only content

`apps/web/src/EnglishOnly.tsx` wraps text that cannot be translated yet: long prose, uncoded backend prose (judge reason, `fresh_status`, setup progress) and docs/evidence text. In English it only adds `lang="en"`; in other languages it also shows the `shell.englishOnly` note. API and case data is never wrapped.

## Intentional English output changes

Phase 1 routes all number and duration formatting through `Intl`, which changed some English output. These changes are deliberate:

- Durations use a space and SI units: "12 ms", "<1 ms" (previously "0ms"), "1.25 s".
- Signed percentage-point deltas show "0.0 pp" for zero.
- Counts are grouped, e.g. "1,440".
- Singular forms are fixed: "1 matching question", "1 paired case".
- Astra verdicts are capitalised ("Correct").
- Prediction status reads "transport error".

## Test data flow

Test data is built per language. English paths and bytes are unchanged (golden digests in `tests/test_english_baseline.py`); every other language lives in `.arena/datasets/<lang>/`.

```
locales/<lang>/prompts.yaml ──> generators (arena/fresh.py, arena/episodes.py, lang=...) ──> generated cases (on demand)
locales/<lang>/datasets.yaml ─┬> arena/i18n/native.py      (pinned HF files, stratified sample)        ─┐
                              └> arena/i18n/translated.py  (English pack + engines + memory)             ├> arena/i18n/packs.py ──> .arena/datasets/<lang>/<pack>-cases.jsonl + manifest
                                      engines.py: manual, opus-mt, deepl, google; memory.py: .arena/translations/<lang>/<slot>.jsonl ┘
arena/suites.py: suite(preset, lang), inventory(lang)  ──>  arena/controller.py (run) ──> manifest["language"]
```

- **Prompts.** `arena/i18n/prompts.py` loads `prompts.yaml` strictly: `prompt(lang, key, **params)` uses `str.format`, and `labels(lang, group)` returns stable id to localized label. A missing key raises `KeyError("<lang>:<key>")`; there is no English fallback.
- **Generators.** `fresh()`, `robustness()` and the episodes take `lang`. The logic and random draws are shared, so golds and proof fields are identical across languages; only strings come from `prompts.yaml`. Choice cases carry `language`, an id prefix `<lang>:` and `provenance["label_ids"] = {localized label: stable id}`. Binary labels stay `no`/`yes` and score labels `0`..`4`.
- **Datasets.** `arena/i18n/datasets.py` validates `datasets.yaml` (slot sources `native`, `translated`, `generated`, `missing`) and computes `expected_counts(lang)`.
- **Native builder.** `arena/i18n/native.py` downloads the pinned files (no dataset scripts), pools and filters rows, samples with the same stratified algorithm as `arena/importers.py` and builds localized choice cases.
- **Translated builder.** `arena/i18n/translated.py` reads the prepared English pack, collects the unique texts, translates the missing ones through an engine into the translation memory, and rebuilds the cases (JSON states: label ids localized, code-like values kept with provenance `untranslated_json_values`, prose translated; `needs_review` recorded in provenance). Rejected memory rows count as missing.
- **Packs.** `arena/i18n/packs.py` `prepare_language(lang, progress, only=None)` builds every non-missing slot, skips translated slots that cannot be built and reports them, and writes per-pack files and manifests with the language, revisions and licences. `arena/setup.py` runs it after the English datasets for the selected language.
- **Suite.** `arena/suites.py` `suite(preset, lang)` assembles Smoke (36 generated cases), Demo (Smoke plus the first 84 JevBench) and Full from the language's packs and the expected counts. `inventory(lang)` returns the per-slot readiness shown in Setup.
- **Run language.** The controller records `manifest["language"]` at run start (runs without it are English). Resumed and saved runs use it for case generation and reports.
- **Episode id mapping.** Warehouse and Tickets show localized choices to the model but keep stable ids internally: the episode maps the selected label back with `provenance["label_ids"]` and records `answer_id` in the trace, so transitions and scoring never depend on the language.
- **ABCD.** A separate frozen assessment with its own runner; it is `missing` for non-English languages.

## Later phases

Reports and further translation workflows are planned in the [design spec](../superpowers/specs/2026-10-04-i18n-design.md). Those phases will extend this document.
