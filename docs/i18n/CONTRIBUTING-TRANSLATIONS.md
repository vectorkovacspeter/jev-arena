# Contributing translations

## 1. Overview

Each language lives in `locales/<code>/`. In Phase 1 a locale has two files:

- `locale.json`: metadata (`code`, `name`, `nativeName`, `status`, `review`, `dir`). `status` is `beta` or `complete`; `code` must equal the directory name.
- `ui.json`: the interface strings, a nested JSON object (i18next JSON v4). `locales/en/ui.json` is the source of truth. A missing or empty string falls back to English at runtime.

Test data (`prompts.yaml`, `datasets.yaml`) is described in section 8 below. Report text arrives in a later phase (see the [design spec](../superpowers/specs/2026-10-04-i18n-design.md)). Until then, backend prose that is not coded (for example some setup progress messages) stays in English and is marked "English only" in the UI.

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

## 8. Language-specific test data

A language can also have its own test data, so models are evaluated on questions in that language. Everything lives in `locales/<code>/`: `prompts.yaml` (repo-authored text for generated cases) and `datasets.yaml` (where each dataset slot comes from). Generated packs and downloaded or translated text go to `.arena/datasets/<code>/` and are never committed. The slot reference, with the Hungarian mapping and reasons, is [DATASET-SLOTS.md](DATASET-SLOTS.md); the data flow is in [ARCHITECTURE.md](ARCHITECTURE.md).

Use `uv run --frozen` for every command. `check` validates both files (placeholders, label groups, slot schema).

### 8.1 Write `prompts.yaml`

Copy `locales/en/prompts.yaml` and translate the values. Rules:

- Same keys as `en`. Placeholders are Python `{name}` fields (the UI catalogs use `{{name}}`). Write a literal brace as `{{` or `}}`. The placeholder set of each key must equal English.
- It is **strict**: a missing or empty key makes generation fail with an error such as `hu:fresh.family0.state`. There is no English fallback in test data, because a language must never silently mix into another's. (The UI does fall back to English.)
- Quote every scalar: unquoted `yes`/`no` load as YAML booleans. The yes/no words are the keys `"yes"` and `"no"`.
- `labels.<group>` maps a **stable id** (the English label) to the localized label. The group's ids must equal English's and the localized values must be unique.
- **Labels inside policy text must equal the group values exactly.** The model must output the label, and the gold answer is looked up by it. If a policy says "Review", the Hungarian text must contain the exact value of `labels.fresh_choice.Review`, in the same inflection.
- Binary (`noul`) questions keep the labels `no`/`yes` in every language (they are protocol ids); only the question text is localized. Score questions keep `0`..`4`.
- Keep the exact logic, precedence and facts of the English sentence: gold answers derive from it. Use natural wording and follow the glossary.

```bash
uv run --frozen python -m arena.i18n check --lang hu
```

### 8.2 Map slots in `datasets.yaml`

Each slot has a `source`:

| source | meaning | needed fields |
|---|---|---|
| `native` | a dataset in your language, pinned on the Hugging Face Hub | `repo`, `revision` (a commit sha), `files`, `fields` (text/premise/hypothesis/label/id to column), `sample`; usually `label_group`, `source_label_ids`, `question`, `licence`; optional `config`, `drop_labels`, `question_id`, `state`, `seed` |
| `translated` | the English pack translated and reviewed | `sample` (or `cases`), optional `engine`, `needs_review`, `label_group`, `question`, `state`, `licence` |
| `generated` | built from `prompts.yaml` (`fresh`, `robustness`, `episodes`) | none |
| `missing` | no data yet | `reason` (required) |

`expected_counts` (the Full preset size) is the sum of `cases`, else `sample`, over non-missing slots, plus the generated counts; episodes are dynamic and not counted. Hungarian Full is 6871 cases. `needs_review: true` marks slots whose machine output (JSON states, label sets) must be reviewed before results are trusted; it is recorded in each case's provenance. Use `cases` when the expected number of cases differs from `sample`.

### 8.3 Find native datasets and check licences

Look on the Hugging Face Hub for a dataset in your language with the same task type and public labels (see "What makes a native substitute acceptable" in [DATASET-SLOTS.md](DATASET-SLOTS.md)). Then:

1. Pin the exact commit: `uv run --frozen python -c "from huggingface_hub import HfApi; print(HfApi().dataset_info('NYTK/HuSST').sha)"`.
2. Read the card **and** the repository's licence file. Record the terms in `licence:`. If they disagree, say so in the value and treat the stricter terms as binding.
3. Check the label balance of the split you plan to use before choosing it. Test splits without public labels are not usable.
4. Add the source and licence to `THIRD_PARTY.md`.

Dataset scripts are never executed; only data files (parquet, json, jsonl, tsv) are read.

### 8.4 Prepare English data first

Translated slots are built from the prepared English packs. Prepare them once:

```bash
uv run --frozen python -m arena.setup --models uniform --skip-workers
```

This downloads and freezes the English datasets (the `uniform` baseline has no weights) and then builds the selected language. The same step is **Prepare selected** in the Setup page. Without the English data, `translate` and `prepare` report `prepare English datasets first`.

### 8.5 Translate

First see how much text there is:

```bash
uv run --frozen python -m arena.i18n translate --lang hu --slot banking77 --dry-run
```

The dry run prints the number of unique texts, how many are not yet in the translation memory, and the number of characters. Then choose an engine with `--engine` (default: the slot's `engine`):

- **opus-mt** (local, free): Helsinki-NLP Marian models, pinned in `arena/i18n/engines.py`. It needs the optional extra, and plain `uv run --frozen` would resync to the default extras, so add the extra to every command:

  ```bash
  uv sync --frozen --extra dev --extra i18n
  uv run --frozen --extra dev --extra i18n python -m arena.i18n translate --lang hu --slot banking77 --engine opus-mt
  ```

  The `i18n` extra conflicts with the `abcd` extra (which pins `tokenizers`) and downgrades `huggingface-hub`. Switch back with `uv sync --frozen --extra dev`. The model splits texts longer than about 200 tokens on sentence boundaries, because longer inputs made it silently drop content.
- **deepl** and **google**: put `DEEPL_API_KEY` (keys ending in `:fx` use the Free endpoint) or `GOOGLE_TRANSLATE_API_KEY` in `.env`. Keys are read from the environment and never logged. DeepL API Free and Google Cloud Translation each include about 500,000 characters per month free, so use `--dry-run` to see whether a slot fits (for example SciFact is about 738,000 characters).
- **manual**: writes `.arena/translations/<lang>/<slot>.pending.jsonl` (`src_sha256`, `src`) and stops. Add a `tgt` to each row (or a file with `src_sha256` and `tgt`), then run `tm import` (section 8.7).

Translations are stored in a translation memory, `.arena/translations/<lang>/<slot>.jsonl`, so reruns only translate what is missing. Nothing is overwritten.

JSON states (JevBench) keep their keys. Each string value is classified: a label id becomes its localized label, a code-like value (`ORD4711`, `escalate_to_manager`) is kept in English and listed in `provenance.untranslated_json_values`, and natural language is translated. Review such slots before trusting results (`needs_review`).

### 8.6 Review

```bash
uv run --frozen python -m arena.i18n review --lang hu --slot banking77 --sample 20
```

It shows a random sample (`--seed`, default 5090) of unreviewed rows with the English source. Answer `y` (correct), `n` (give a corrected translation, or leave it empty to reject), `e` (edit) or `q` (quit). Reviewed rows are marked, rejected rows count as **missing** and are retranslated or filled with `tm import`.

### 8.7 Share a translation memory

```bash
uv run --frozen python -m arena.i18n tm export --lang hu --slot banking77 banking77-hu.jsonl
uv run --frozen python -m arena.i18n tm import --lang hu --slot banking77 banking77-hu.jsonl
```

Each row has `src_sha256`, `src`, `tgt` and optional `reviewed`, `engine`, `model`, `revision`. Imported rows replace existing translations and clear a rejection; rows resolved from a manual pending file are removed from it. Share only translations you have the right to share (the English source text is not redistributed by Arena; see `THIRD_PARTY.md`).

### 8.8 Prepare the language

```bash
uv run --frozen python -m arena.i18n prepare --lang hu
uv run --frozen python -m arena.i18n prepare --lang hu --only native
```

`prepare` builds every non-missing slot into `.arena/datasets/<lang>/`. `--only native|translated|generated` limits it. A translated slot that cannot be built (no English data, no translations yet, engine unavailable) is **skipped and reported** and the rest continue; `prepare` also runs after English data in Setup. Native slots work without English data.

### 8.9 Run Smoke in the new language

1. Set the language in the header.
2. Open Setup and use **Prepare selected**.
3. Run **Smoke**. It uses only generated fixtures, so it works as soon as `prompts.yaml` is complete. **Full** needs every non-missing slot prepared.

The run records its language in the manifest (`manifest["language"]`; runs without it are English). Local cases carry `language=<code>` and ids prefixed `<code>:`; episodes map the localized answers back to stable ids. The UI shows the data language, a slot table (source, licence, readiness) and a badge when the run language is not English.

### 8.10 What "complete" means for test data

- `check` reports no errors and no warnings for `prompts.yaml` and `datasets.yaml`.
- Every slot is non-missing, or missing with a justified `reason` (for example ABCD is a separate frozen assessment).
- Every translated slot has a reviewed sample (use `review`; at least 20 reviewed rows per slot is a reasonable floor) and, for `needs_review` slots, the review is done before results are quoted.
- Native slots have a pinned revision and a recorded licence, and the label balance was checked.
- Smoke runs, and the Full preset reaches its `expected_counts`.
- A native speaker has reviewed `prompts.yaml`; then update `review` in `locale.json`.
