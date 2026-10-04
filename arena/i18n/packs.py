"""Per-language packs: .arena/datasets/<lang>/<pack>-cases.jsonl plus a manifest.

Mirrors arena.importers (which stays untouched for English): same stratified sampling, same save
checks, plus the language and the slot licences in the manifest.
"""
from __future__ import annotations
import random
from collections import defaultdict
from typing import Callable
from arena.config import DATASETS, digest, write_json
from arena.contracts import Case
from arena.i18n.datasets import Slot, load_slots
from arena.i18n.engines import EngineError, Unavailable

# English pack name -> file name, one file per English pack.
PACK_FILES = {"JevBench public": "jevbench", "Typed decisions": "typed", "Classification": "classification",
              "Multilingual": "multilingual", "RAG relevance": "rag"}
SOURCES = ("native", "translated", "generated")

def stratified(rows, count, key="label", seed=5090):
    """Same algorithm as arena.importers.stratified (round-robin over sorted groups of shuffled indices)."""
    groups = defaultdict(list)
    for i, row in enumerate(rows): groups[row[key]].append(i)
    rng = random.Random(seed)
    for ids in groups.values(): rng.shuffle(ids)
    selected = []
    keys = sorted(groups, key=str)
    while len(selected) < count:
        changed = False
        for k in keys:
            if groups[k]: selected.append(groups[k].pop()); changed = True
            if len(selected) == count: break
        if not changed: raise ValueError("Insufficient rows for stratified sample")
    return sorted(selected)

def pack_dir(lang: str):
    return DATASETS / lang

def read_pack(lang: str, pack_file: str) -> list[Case]:
    path = pack_dir(lang) / f"{pack_file}-cases.jsonl"
    if not path.exists(): return []
    return [Case.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def save(lang: str, pack_file: str, cases: list[Case], expected: int, licences: dict | None = None, revisions: dict | None = None):
    if len(cases) != expected: raise ValueError(f"{lang}/{pack_file}: expected {expected}, got {len(cases)}")
    if len({c.id for c in cases}) != len(cases): raise ValueError("Duplicate source IDs")
    folder = pack_dir(lang); folder.mkdir(parents=True, exist_ok=True)
    raw = "\n".join(c.model_dump_json() for c in cases) + "\n"
    path = folder / f"{pack_file}-cases.jsonl"; temp = path.with_suffix(".tmp"); temp.write_text(raw, encoding="utf-8"); temp.replace(path)
    write_json(folder / f"{pack_file}-manifest.json", {"version": "arena-v1", "language": lang, "count": len(cases), "sha256": digest(raw.encode()),
                                                       "source_revisions": revisions or {}, "licences": licences or {}, "case_ids": [c.id for c in cases]})

def _build(lang: str, slot_id: str, slot: Slot, progress: Callable[[str], None]) -> list[Case]:
    if slot.source == "native":
        from arena.i18n import native
        return native.build(lang, slot_id, slot)
    if slot.source == "translated":
        from arena.i18n import translated
        return translated.prepare_slot(lang, slot_id, slot, progress)
    raise NotImplementedError(f"{slot.source} slots are not buildable yet")

def prepare_language(lang: str, progress: Callable[[str], None] | None = None, only: str | None = None) -> dict[str, int]:
    """Build the language's native and translated slots into one file per English pack.

    Generated slots need no files: they are produced on demand from prompts.yaml. Translated slots need the
    English packs; a translated slot that cannot be built now (English not prepared, engine unavailable or failing,
    manual translations pending, missing or colliding translations) is reported and skipped. Rebuilding a subset of slots keeps the cases of the other slots already in a
    pack file. Returns {pack_file: cases written}.
    """
    if lang == "en": raise ValueError("English packs are built by arena.importers")
    say = progress or (lambda message: None)
    if only is not None and only not in SOURCES: raise ValueError(f"only must be one of {SOURCES}")
    slots = load_slots(lang)
    built: dict[str, dict[str, list[Case]]] = defaultdict(dict)
    for slot_id, slot in slots.items():
        if slot.source == "missing" or (only and slot.source != only): continue
        if slot.source == "generated": say(f"{slot_id}: generated on demand"); continue
        if slot.pack not in PACK_FILES: raise ValueError(f"{slot_id}: no pack file for pack {slot.pack!r}")
        try: cases = _build(lang, slot_id, slot, say)
        except (NotImplementedError, Unavailable) as e: say(f"{slot_id}: skipped ({e})"); continue
        except (EngineError, ValueError) as e:  # LabelCollision, MissingTranslations, engine failures: the other slots still build
            if slot.source != "translated": raise
            say(f"{slot_id}: failed, skipped ({type(e).__name__}: {e})"); continue
        if slot.expected() is not None and len(cases) != slot.expected():
            raise ValueError(f"{slot_id}: expected {slot.expected()}, got {len(cases)}")
        built[PACK_FILES[slot.pack]][slot_id] = cases
        say(f"{slot_id}: {len(cases)} cases")
    order = list(slots)
    result = {}
    for pack_file, fresh_slots in built.items():
        by_slot: dict[str, list[Case]] = defaultdict(list)
        for case in read_pack(lang, pack_file):
            sid = case.provenance.get("slot")
            if sid in slots and sid not in fresh_slots and slots[sid].source != "missing": by_slot[sid].append(case)
        by_slot.update(fresh_slots)
        ids = sorted(by_slot, key=order.index)
        cases = [c for sid in ids for c in by_slot[sid]]
        licences = {sid: slots[sid].licence for sid in ids}
        revisions = {slots[sid].repo: slots[sid].revision for sid in ids if slots[sid].repo}
        save(lang, pack_file, cases, sum(len(by_slot[sid]) for sid in ids), licences, revisions)
        say(f"{lang}/{pack_file}: {len(cases)} cases frozen")
        result[pack_file] = len(cases)
    return result
