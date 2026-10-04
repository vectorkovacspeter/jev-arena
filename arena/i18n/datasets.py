"""Dataset slots per language (locales/<lang>/datasets.yaml).

A slot is one source of test cases (an English pack/family). Each language says how it fills it:
native (a dataset in that language, pinned on the Hugging Face Hub), translated (from the prepared
English pack), generated (from prompts.yaml, built on demand) or missing (with a reason).
The en file is descriptive: English packs are still built by arena.importers.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, ConfigDict, model_validator
from arena.i18n.locales import LOCALES

FILE = "datasets.yaml"

class Slot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["native", "translated", "generated", "missing"]
    pack: str
    family: str
    reason: str | None = None                     # required when missing
    repo: str | None = None
    revision: str | None = None
    config: str | None = None
    files: list[str] = []                          # repo-relative parquet/json/jsonl/tsv paths (native)
    fields: dict[str, str] = {}                    # text/premise/hypothesis/label/id -> column
    sample: int | None = None                      # rows to sample (native) or cases (translated)
    cases: int | None = None                       # expected cases when they differ from sample (en: rows x languages)
    seed: int = 5090
    drop_labels: list[str] = []                    # raw source label values to drop before sampling
    label_group: str | None = None                 # prompts.yaml labels.<group>
    source_label_ids: dict[str, str] = {}          # raw dataset label value (as string) -> stable id
    question: str | None = None                    # prompts.yaml key of the question text
    question_id: str = "label"                     # Question.id, as in the English pack
    state: str | None = None                       # prompts.yaml key for a multi-field state
    licence: str = ""
    engine: str | None = None                      # translated: default engine
    needs_review: bool = False                     # translated: machine output must be reviewed before results are trusted (recorded in provenance)

    @model_validator(mode="after")
    def required_fields(self):
        if self.source == "missing" and not self.reason: raise ValueError("a missing slot needs a reason")
        if self.source == "native":
            absent = [name for name in ("repo", "revision", "files") if not getattr(self, name)]
            if absent: raise ValueError(f"a native slot needs {', '.join(absent)}")
        return self

    def expected(self) -> int | None:
        return self.cases if self.cases is not None else self.sample

class LanguageDatasets(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slots: dict[str, Slot]

def _root() -> Path: return LOCALES  # read at call time so tests can monkeypatch it

def has_slots(lang: str) -> bool: return (_root() / lang / FILE).exists()

def parse(data) -> dict[str, Slot]:
    return LanguageDatasets.model_validate(data).slots

def load_slots(lang: str) -> dict[str, Slot]:
    path = _root() / lang / FILE
    if not path.exists(): raise FileNotFoundError(f"{lang}: no {FILE} (no dataset slots for this language)")
    return parse(yaml.safe_load(path.read_text(encoding="utf-8")))

@lru_cache(maxsize=None)
def _generated_count(slot_id: str, lang: str) -> int | None:
    from arena.fresh import fresh, robustness
    generators = {"fresh": fresh, "robustness": robustness}
    return len(generators[slot_id](lang=lang)) if slot_id in generators else None  # episodes are dynamic

def expected_counts(lang: str, slots: dict[str, Slot] | None = None) -> dict[str, int]:
    """Pack name -> expected cases in the Full preset. Missing slots, dynamic episodes and slots without a count are left out."""
    counts: dict[str, int] = {}
    for slot_id, slot in (load_slots(lang) if slots is None else slots).items():
        if slot.source == "missing": continue
        n = _generated_count(slot_id, lang) if slot.source == "generated" else slot.expected()
        if n is None: continue
        counts[slot.pack] = counts.get(slot.pack, 0) + n
    return counts
