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

Keys assembled at runtime (`errors.*`, `readiness.*`, `packs.*`, `families.*`, `status.*`, `nav.*` via `pageKeys` in `navigation.ts`, `results.verdicts`, `operations.{directions,queues,topics}`, `explore.{types,errors}`, `abcd.{errors,conditions}`) are invisible to `i18next-parser`. `i18next-parser.config.js` protects them with `keepRemoved` patterns built from the `dynamic` list. The parser tests `translation:<key>` (namespace separator `:`), which is why the patterns start with `^translation:`. Add every new family there.

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

## Later phases

Reports, prompts, dataset mapping, language-aware suites and translation engines are planned in the [design spec](../superpowers/specs/2026-10-04-i18n-design.md). Those phases will extend this document.
