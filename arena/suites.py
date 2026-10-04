from __future__ import annotations
import json
from collections import Counter
from arena.config import DATASETS, SOURCES, digest, write_json
from arena.contracts import Case, Question
from arena.fresh import fresh, smoke, robustness
from arena.i18n.errors import ArenaError

FRESH_STATUS = "Executable-policy fixtures v2: new seed, explicit routing and approval rules. Human semantic audit not claimed."
# Packs whose slots are told apart by case family (English cases carry no provenance["slot"]).
FAMILY_SLOTTED = ("Classification", "Multilingual")
NO_CONFIG = "no datasets.yaml"

EXPECTED = {"JevBench public":231,"Typed decisions":2000,"Classification":1500,"Multilingual":1000,"RAG relevance":500,"Arena Fresh":1440,"Robustness":1000}

def jevbench():
    out=[]
    for tier in ("original","easy","hard"):
        path=SOURCES/"jevbench"/"datasets"/"public"/f"{tier}.jsonl"
        if not path.exists(): continue
        for line in path.read_text(encoding="utf-8").splitlines():
            x=json.loads(line);q=x["question"]
            x["group"]=x.get("group") or x["id"]
            criteria=q.get("criteria",{})
            out.append(Case(id="jevbench-"+x["id"],cluster="jevbench-"+x.get("group",x["id"]),pack="JevBench public",family=x["family"],state=x["state"] if isinstance(x["state"],str) else json.dumps(x["state"]),question=Question(id="decision",text=q["instructions"],kind=q["type"],labels=x["labels"],rubric=json.dumps(criteria,ensure_ascii=False)),gold=str(x["expected"]),label_status="public",provenance={**x.get("provenance",{}),"tier":tier,"file_sha256":digest(path.read_bytes()),"native_question":q}))
    for case in out:
        case.question.criteria=case.provenance["native_question"].get("criteria")
    return out

def imported():
    result=[]
    for path in sorted(DATASETS.glob("*-cases.jsonl")):
        result.extend(Case.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return result

def suite(preset, lang="en"):
    if lang != "en": return localized_suite(preset, lang)
    if preset=="smoke": cases=smoke()
    elif preset=="demo":
        pool=jevbench()
        if len(pool)<84:raise ArenaError('demo_needs_sources','Demo needs the pinned public JevBench sources. Use Prepare selected in Setup first.')
        cases=smoke()+pool[:84]
    else:
        cases=jevbench()+imported()+fresh()+robustness()
        counts=Counter(c.pack for c in cases)
        missing={k:{"expected":v,"available":counts.get(k,0)} for k,v in EXPECTED.items() if counts.get(k,0)!=v}
        if missing: raise ArenaError("suite_not_prepared","Full suite is not prepared: "+json.dumps(missing),missing=json.dumps(missing),packs=missing)
    if len({c.id for c in cases})!=len(cases): raise ArenaError("duplicate_case_ids","Duplicate case IDs in suite")
    return cases

def inventory(lang="en"):
    if lang != "en": return localized_inventory(lang)
    cases=jevbench()+imported()+fresh()+robustness()
    counts=Counter(c.pack for c in cases)
    result={"version":"arena-v2","expected":7671,"available":sum(counts.values()),"packs":[{"name":k,"expected":v,"available":counts[k],"ready":counts[k]==v} for k,v in EXPECTED.items()],"presets":[{"id":"smoke","count":36,"ready":True},{"id":"demo","count":120,"ready":counts['JevBench public']>=84},{"id":"full","count":7671,"ready":all(counts[k]==v for k,v in EXPECTED.items())}],"fresh_status":FRESH_STATUS}
    # Additive keys; everything above is the pre-i18n English inventory, unchanged.
    from arena.i18n.datasets import load_slots
    return {**result,"language":"en","slots":slot_rows(load_slots("en"),cases,EXPECTED)}

# Non-English suites: packs from .arena/datasets/<lang>/ plus generated fresh/robustness cases.
# The English path above stays as it was; these functions only run for other languages.

def localized_packs(lang):
    from arena.i18n.packs import pack_dir
    result = []
    for path in sorted(pack_dir(lang).glob("*-cases.jsonl")):
        result.extend(Case.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return result

def localized_jevbench(lang):
    from arena.i18n.packs import read_pack
    return read_pack(lang, "jevbench")

def localized_suite(preset, lang):
    from arena.i18n.datasets import expected_counts
    if preset == "smoke": cases = smoke(lang)
    elif preset == "demo":
        pool = localized_jevbench(lang)
        if len(pool) < 84: raise ArenaError('demo_needs_sources', 'Demo needs the pinned public JevBench sources. Use Prepare selected in Setup first.')
        cases = smoke(lang) + pool[:84]
    else:
        cases = localized_packs(lang) + fresh(lang=lang) + robustness(lang)
        counts = Counter(c.pack for c in cases)
        missing = {k: {"expected": v, "available": counts.get(k, 0)} for k, v in expected_counts(lang).items() if counts.get(k, 0) != v}
        if missing: raise ArenaError("suite_not_prepared", "Full suite is not prepared: " + json.dumps(missing), missing=json.dumps(missing), packs=missing, language=lang)
    if len({c.id for c in cases}) != len(cases): raise ArenaError("duplicate_case_ids", "Duplicate case IDs in suite")
    return cases

def slot_rows(slots, cases, expected):
    """Per-slot readiness. Cases are matched by provenance["slot"] when present, else by family (FAMILY_SLOTTED packs) or pack."""
    by_slot = Counter(c.provenance.get("slot") for c in cases if c.provenance.get("slot"))
    by_family = Counter((c.pack, c.family) for c in cases if not c.provenance.get("slot"))
    by_pack = Counter(c.pack for c in cases)
    rows = []
    for slot_id, slot in slots.items():
        if slot.source == "missing": want, have, ready = None, 0, False
        elif slot.source == "generated":
            want = expected.get(slot.pack)  # None for dynamic episodes
            have, ready = (by_pack.get(slot.pack, 0) if want is not None else None), True
        elif slot.pack not in expected: want, have, ready = None, 0, False  # not part of the Full preset (e.g. English ABCD)
        else:
            want = slot.expected()
            if slot.pack in FAMILY_SLOTTED: have = by_slot.get(slot_id, 0) + by_family.get((slot.pack, slot.family), 0)
            else: have = by_slot.get(slot_id, 0) + sum(n for (pack, _), n in by_family.items() if pack == slot.pack)
            ready = have == want
        rows.append({"slot": slot_id, "pack": slot.pack, "family": slot.family, "source": slot.source, "ready": ready,
                     "expected": want, "available": have, "licence": slot.licence, "reason": slot.reason})
    return rows

def localized_inventory(lang):
    from arena.i18n.datasets import Slot, expected_counts, has_slots, load_slots
    packed = localized_packs(lang)
    if has_slots(lang):
        slots, expected = load_slots(lang), expected_counts(lang)
        cases = packed + fresh(lang=lang) + robustness(lang)
    else:  # a language without datasets.yaml has no test data yet: every slot is missing
        slots = {sid: Slot(source="missing", pack=s.pack, family=s.family, reason=NO_CONFIG) for sid, s in load_slots("en").items()}
        expected, cases = {}, packed
    counts = Counter(c.pack for c in cases)
    total = sum(expected.values())
    jev = sum(1 for c in packed if c.pack == "JevBench public")
    full_ready = bool(expected) and all(counts.get(k, 0) == v for k, v in expected.items())
    try: small, smoke_ready = len(smoke(lang)), True
    except Exception: small, smoke_ready = 36, False  # prompts.yaml lacks the language
    return {"version": "arena-v2", "language": lang, "expected": total, "available": sum(counts.get(k, 0) for k in expected),
            "packs": [{"name": k, "expected": v, "available": counts.get(k, 0), "ready": counts.get(k, 0) == v} for k, v in expected.items()],
            "slots": slot_rows(slots, cases, expected),
            "presets": [{"id": "smoke", "count": small, "ready": smoke_ready}, {"id": "demo", "count": small + 84, "ready": smoke_ready and jev >= 84},
                        {"id": "full", "count": total, "ready": full_ready}],
            "fresh_status": FRESH_STATUS}
