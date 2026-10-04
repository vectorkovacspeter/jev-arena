# Contributing translations

## 1. Overview

Each language lives in `locales/<code>/`. In Phase 1 a locale has two files:

- `locale.json`: metadata (`code`, `name`, `nativeName`, `status`, `review`, `dir`). `status` is `beta` or `complete`; `code` must equal the directory name.
- `ui.json`: the interface strings, a nested JSON object (i18next JSON v4). `locales/en/ui.json` is the source of truth. A missing or empty string falls back to English at runtime.

Report text, model prompts and dataset mapping arrive in later phases (see the [design spec](../superpowers/specs/2026-10-04-i18n-design.md)). Until then, backend prose that is not coded (for example some setup progress messages) stays in English and is marked "English only" in the UI.

## 2. Add a new language

Use `uv run --frozen` so running the tools never rewrites `uv.lock`.

```bash
uv run --frozen python -m arena.i18n new-language pl --name Polish --native Polski
# translate locales/pl/ui.json (empty strings fall back to English)
uv run --frozen python -m arena.i18n check --lang pl
npm run build && npm run dev
```

`<code>` must match `^[a-z]{2,3}(-[A-Z]{2})?$` (for example `pl`, `pt-BR`). The command creates `locales/<code>/locale.json` (status `beta`, review `needs native review`) and a `ui.json` with every key set to an empty string.

`check` prints errors and warnings, then one summary line per language, for example `hu ui.json: 100.0% complete (0 missing)`. Add `--quiet` to print errors only. It exits with status 1 when there are errors (unknown keys, mismatched `{{placeholders}}`, a plural group without `_other`, a broken or mismatched `locale.json`). Missing translations are warnings, not errors. The same check runs in CI.

A locale whose `locale.json` is broken, or whose `code` differs from its directory name, is skipped by the app (it never breaks startup) but is reported by `check`.

The language appears in the header switcher automatically. The choice is stored globally in `.arena/settings.json` as `{"language": "<code>"}`.

## 3. Catalog rules

- Keep keys and `{{placeholders}}` exactly as in `en`. `check` fails when the placeholder sets differ.
- Plurals use i18next suffixes: `_one` and `_other`, plus `_zero`, `_two`, `_few`, `_many` where your language needs them under CLDR (the browser's `Intl.PluralRules` decides which are used). An `_other` form is always required. English and Hungarian use only `_one` and `_other`.
- Keep the `<b>...</b>`-style tags that appear in `Trans` strings (for example `<b>`, `<link>`). Translate the text between them but do not rename, remove or reorder them into invalid nesting.
- Do not translate product and model names or the metric acronyms (F1, Brier, MAE, P95, nDCG@10, MRR). See the glossary.
- Prefer wording that avoids number-dependent grammar (suffix agreement, articles) because values are interpolated.
- Numbers, percentages, durations and dates are formatted by the app (`Intl`), so never hard-code separators in a string.

## 4. beta versus complete

New languages start as `beta`; the UI shows a "beta" tag next to them. A language may be set to `complete` when:

1. `uv run --frozen python -m arena.i18n check --lang <code>` reports no errors and no warnings (100.0% complete), and
2. a native speaker has reviewed it. Set `review` in `locale.json` to the reviewer's name or handle (replacing `needs native review`) and change `status` to `complete`.

## 5. Adding UI strings as a developer

1. Use `t("namespace.key")` (and `<Trans>` for strings with inline markup) from `useTranslation()`; use `useFormat()` for numbers, percentages, durations and dates. Never write literal text in JSX.
2. Run `npm run i18n:extract`. It adds new keys to `locales/en/ui.json` only, with the English text as default.
3. Run `npm run i18n:lint`. It fails on literal strings in JSX text and in the `title`, `aria-label`, `placeholder` and `alt` attributes. CI runs it.
4. Other locales are not rewritten by extract. Add the new keys to them manually, or leave them to fall back to English. `uv run --frozen python -m arena.i18n check` lists what is missing.
5. Keys built at runtime (for example `` t(`packs.${slug}`) ``) cannot be seen by the parser, and extract would delete them. Every dynamic key family must be listed in the `dynamic` array in `i18next-parser.config.js` (a key that is only reserved for upcoming code goes in `reserved`). Review `git diff locales/en/ui.json` after extracting to be sure nothing was removed.
6. Backend errors: raise `ArenaError(code, message, **params)` / `ArenaHTTPError(status, code, message, **params)` and add `errors.<code>` to the catalogs. See [ARCHITECTURE.md](ARCHITECTURE.md).

## 6. Glossaries

Each language may keep a glossary at `docs/i18n/glossary-<code>.md` so contributors translate recurring terms the same way. The Hungarian one, [glossary-hu.md](glossary-hu.md), is the example.

## 7. Translation platforms

`ui.json` files are plain i18next JSON v4 and can be imported directly into Weblate or Crowdin. Keep `en` as the source file and export the translated files back to `locales/<code>/ui.json`, then run `check`.
