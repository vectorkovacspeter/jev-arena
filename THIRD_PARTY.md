# Attribution and licenses

Only original Arena source, documentation and owned fixtures are distributed. Checkpoints, datasets, reference archives and YouTube transcripts stay in the ignored private cache. Their original terms apply independently of Arena's MIT license.

| Component | Original source / terms |
|---|---|
| Jev | [TypeSafe](https://typesafe.ai), proprietary service |
| Plumb / JevK5 | [Model](https://huggingface.co/crh225/plumb-4b), [runtime](https://github.com/allebee/jevk5), Apache-2.0 |
| Decider | [Model card](https://huggingface.co/Mapika/decider-4b), [runtime](https://github.com/Mapika/decider); consult selected release terms |
| Laya | [Models](https://huggingface.co/convaiinnovations/laya), [runtime](https://github.com/NandhaKishorM/laya), Apache-2.0 |
| SemIf | [Runtime](https://github.com/TheoLeeCJ/SemIf-OpenJev), MIT; Qwen3.5 base, Apache-2.0 |
| Nimble | [Model](https://huggingface.co/bespokelabs/Bespoke-Nimble-9B), [runtime](https://github.com/bespokelabsai/nimble), Apache-2.0 |
| CLM | [Heads](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B), [runtime](https://github.com/Contrastive-LM/CLM), Qwen3 base |
| Winnow | [Model](https://huggingface.co/EldanRing/Winnow-12B), [runtime](https://github.com/EldanRing/winnow-inference); Gemma-derived weight terms apply |
| NLI | [ModernBERT card](https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0), Apache-2.0 |
| Datasets | [JevBench](https://github.com/fstandhartinger/jevbench), typed-decisions, SST-2, AG News, BANKING77, MASSIVE, XNLI, SciFact: original cards/revisions are linked in the research and per-case manifests; no text redistribution in report exports |
| ABCD | [ASAPP Research dataset](https://github.com/asappresearch/abcd), [MIT notice](docs/licenses/ABCD-LICENSE.txt). Raw conversations are downloaded separately and not published here. |
| UI/tools | React, Vite, FastAPI, NumPy, Lucide, Codex CLI and dependencies retain their package licenses; versions are locked |
| Fonts | Fontsource Poppins, DM Sans and Space Grotesk, SIL Open Font License |

## Hungarian test data

Hungarian test data (`locales/hu/datasets.yaml`) is downloaded or translated on the user's machine into the ignored `.arena/` cache. **Nothing is redistributed**: no dataset text, translations or translation memories are committed or included in report exports. Native sources are pinned Hugging Face revisions; the licence strings below are quoted exactly from the slots' `licence:` field in `datasets.yaml`, which is also written to the pack manifests.

| Slot | Source | `licence:` (verbatim) |
|---|---|---|
| SST-2 | [NYTK/HuSST](https://huggingface.co/datasets/NYTK/HuSST) | `CC-BY-SA-4.0 (HuSST GitHub LICENSE.md; HF card says BSD-2-Clause — treated as share-alike)` |
| AG News | [Davlan/sib200](https://huggingface.co/datasets/Davlan/sib200), `hun_Latn` (SIB-200) | `CC-BY-SA-4.0 (HF card metadata; card text says "CC 4.0 Commercial")` |
| XNLI | [NYTK/HuCommitmentBank](https://huggingface.co/datasets/NYTK/HuCommitmentBank) | `CC-BY-SA-4.0 (HF card text and LICENSE.txt; no card metadata)` |
| MASSIVE | [AmazonScience/massive](https://huggingface.co/datasets/AmazonScience/massive), `hu-HU` | `CC-BY-4.0` |

Translated derivatives are built from the English sources with a machine translation engine and a reviewed sample; the original terms continue to apply to the translations:

| Slot | English source | `licence:` (verbatim) |
|---|---|---|
| BANKING77 | PolyAI BANKING77 ([legacy-datasets/banking77](https://huggingface.co/datasets/legacy-datasets/banking77), pinned `f54121560de4`) | `CC-BY-4.0 (translation of PolyAI BANKING77)` |
| SciFact | [BeIR/scifact](https://huggingface.co/datasets/BeIR/scifact), pinned `b3b5335604bf` (`arena/importers.py` `PINS`) | `CC-BY-SA-4.0 (translation of BeIR/scifact; HF card metadata)` |
| typed-decisions | [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions), pinned `f7a2487edd7a` | `Apache-2.0 (translation of LocalLLaMA/typed-decisions; HF card metadata)` |
| JevBench | [JevBench public](https://github.com/fstandhartinger/jevbench) | `MIT (translation of JevBench public; repository LICENSE)` |

Machine translation uses [Helsinki-NLP/opus-mt-en-hu](https://huggingface.co/Helsinki-NLP/opus-mt-en-hu) at revision `f2ee4d3f21c0ec85db4eb55d00b3ecc55fbd9d9b`. The model is not redistributed; it is downloaded on demand with the optional `i18n` extra. Its card at the pinned revision states Apache-2.0. DeepL and Google Cloud Translation are optional services under their own terms and are used only with the user's own keys.

No creator transcripts, thumbnails or clips are redistributed. Names and trademarks identify their respective projects and do not imply endorsement.

The interactive HTML report embeds copies of React, React DOM, Scheduler, Lucide icons and the bundled fonts. Their full notices are in [THIRD-PARTY-LICENSES.txt](THIRD-PARTY-LICENSES.txt), retained inside each report and ZIP export alongside Arena's MIT license.
