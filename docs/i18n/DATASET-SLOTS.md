# Dataset slots

A slot is one source of test cases in the Full preset. English fills each slot from an English pack or generator. Every other language declares in `locales/<code>/datasets.yaml` how it fills the slot: `native` (a dataset in that language, pinned on the Hugging Face Hub), `translated` (the English pack, machine-translated and reviewed), `generated` (built from `prompts.yaml`) or `missing` (with a reason). See [CONTRIBUTING-TRANSLATIONS.md](CONTRIBUTING-TRANSLATIONS.md) for how to fill them and [ARCHITECTURE.md](ARCHITECTURE.md) for the data flow.

## What makes a native substitute acceptable

1. **Same task type**: the same kind of question (sentiment, topic, entailment, intent, and so on) with a comparable label set, so the slot measures the same skill.
2. **Labelled data**: public gold labels in a split you can use. Test splits without public labels cannot be used.
3. **A licence that allows local use**: the text is downloaded from the original source and never redistributed (see `THIRD_PARTY.md`), but record the licence in `licence:` and check it allows research use. Where the card and the licence file disagree, document it and treat the stricter terms as binding.
4. **Sample size**: enough rows per label for the stratified sample (`sample:`), ideally the same size as English. The sampler raises "Insufficient rows" otherwise.
5. **Balanced labels** after any filtering. Check the label distribution of the split you pick (see the HuSST note below).

If no such dataset exists, translate the English pack instead, or mark the slot `missing` with an honest reason.

## Slots

| Slot | Measures | English source | Labels | Hungarian |
|---|---|---|---|---|
| `jevbench` | Policy decisions over structured states (public JevBench) | JevBench public | per-case choice labels, JSON states | translated (opus-mt), 231, `needs_review` |
| `typed-decisions` | Typed teacher decisions with native label sets and criteria | `LocalLLaMA/typed-decisions` | per-case choice labels | translated (opus-mt), 2000, `needs_review` |
| `sst2` | Sentiment | `stanfordnlp/sst2` | negative, positive | native `NYTK/HuSST`, train split, neutral dropped, 500 |
| `agnews` | Topic classification | `fancyzhx/ag_news` (4 topics) | 4 topics (en); 7 SIB-200 topics (hu) | native `Davlan/sib200` `hun_Latn`, all splits pooled, 500 |
| `banking77` | Fine-grained banking intent | `legacy-datasets/banking77` | 77 intents | translated (opus-mt), 500 |
| `xnli` | Natural language inference | `facebook/xnli` | entailment, neutral, contradiction | native `NYTK/HuCommitmentBank`, train+validation, 100 |
| `massive` | Assistant intent detection | `AmazonScience/massive` | 60 intents | native `AmazonScience/massive` `hu-HU`, test, 100 |
| `scifact` | Document relevance for a scientific claim | `BeIR/scifact` | Relevant / Not relevant | translated (opus-mt), 500 |
| `fresh` | Formal policy fixtures (8 families, dev/calibration/test) | `arena/fresh.py` | choice, binary, ordinal (0..4) | generated from `prompts.yaml`, 1440 |
| `robustness` | Paraphrase, distractor and injection perturbations | `arena/fresh.py` | as `fresh` | generated, 1000 |
| `episodes` | Warehouse and Tickets workflows | `arena/episodes.py` | directions, queues | generated, dynamic (not in the Full count) |
| `abcd` | ABCD next action | frozen ASAPP assessment | - | missing: separate frozen assessment; Hungarian ABCD is a follow-up |

The Hungarian Full preset has 231 + 2000 + 1500 + 200 + 500 + 1440 + 1000 = **6871** cases (the 1500 classification and 200 multilingual cases come from `sst2`/`agnews`/`banking77` and `xnli`/`massive`). Smoke is 36 generated cases and works immediately; Demo is 120 (Smoke plus the first 84 JevBench).

## Why this hu mapping

- **HuSST train, not validation.** English SST-2 is balanced. The HuSST validation split is 93% negative once the `neutral` rows are dropped (697 negative, 33 positive), so a stratified sample would be nearly empty for one class. The train split gives a balanced 250/250 sample. The test split has no public labels. Neutral rows are dropped because the English slot is binary.
- **SIB-200 for AG News.** SIB-200 is a topic-classification set (Flores-200 sentences) with a Hungarian configuration. Its 7 topics differ from AG News's 4, so the Hungarian slot measures topic classification, not the same label space. The labels live in `labels.sib_topics`.
- **HuCommitmentBank for XNLI.** A native entailment/neutral/contradiction dataset; test labels are not public, so train and validation are used.
- **MASSIVE hu-HU.** The same family as English. The English importer reads a parquet conversion; the Hungarian slot pins the same kind of revision.
- **BANKING77, SciFact, typed-decisions and JevBench are translated.** No Hungarian dataset of the same task and label set exists, so the English pack is translated with a pinned engine and a reviewed sample. JevBench and typed-decisions are marked `needs_review` because their JSON states and label sets are machine-translated; the flag is recorded in each case's provenance.
- **Generated slots** (`fresh`, `robustness`, `episodes`) keep the logic, random draws and golds identical across languages. Only the strings in `prompts.yaml` change.
- **ABCD** is a separate frozen assessment with its own runner, so it is `missing` in Hungarian.

## Label sets

Label groups live in `locales/<code>/prompts.yaml` under `labels.<group>` and map a **stable id** (the English label) to the localized label: `fresh_choice`, `directions`, `ticket_queues`, `sentiment`, `nli`, `sib_topics`, `massive_intents`, `banking77`. Cases carry `provenance["label_ids"] = {localized: stable id}`. Scoring compares the model's answer with the localized gold label (the question offers localized labels, so the answer is localized too); `label_ids` is used by episodes, which step their environment by stable id, and to map localized labels back to their English ids across languages (the UI compares episode answers by `answer_id`). Binary (`noul`) questions keep `no`/`yes` as protocol labels in every language and score questions keep `0`..`4`.

## Licences

Licences are recorded per slot in `datasets.yaml` (`licence:`), shown in the Setup table and written to each pack manifest. See `THIRD_PARTY.md` for the Hungarian sources.
