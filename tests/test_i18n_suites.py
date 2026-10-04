import asyncio
import json
import pytest
from arena import controller as module
from arena import suites
from arena.config import digest
from arena.contracts import Prediction, RunRequest
from arena.fresh import smoke
from arena.i18n import packs, settings
from arena.i18n.errors import ArenaError
from arena.store import Store

@pytest.fixture
def hu_data(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, "DATASETS", tmp_path / "datasets")
    return tmp_path / "datasets" / "hu"

def fixture_cases(pack, slot, n, start=0):
    base = smoke("hu")[0]
    return [base.model_copy(deep=True, update={"id": f"hu:{slot}-{start + i}", "pack": pack, "provenance": {"slot": slot}}) for i in range(n)]

def test_hungarian_smoke_has_36_hungarian_cases():
    cases = suites.suite("smoke", "hu")
    assert len(cases) == 36 and all(c.language == "hu" and c.id.startswith("hu:") for c in cases)

def test_hungarian_full_without_packs_lists_missing(hu_data):
    with pytest.raises(ArenaError) as info: suites.suite("full", "hu")
    e = info.value
    assert e.code == "suite_not_prepared" and e.params["language"] == "hu"
    assert e.params["packs"]["JevBench public"] == {"expected": 231, "available": 0}
    assert e.params["packs"]["Classification"] == {"expected": 1500, "available": 0}
    assert "Arena Fresh" not in e.params["packs"] and "Robustness" not in e.params["packs"]
    assert "ABCD next action" not in e.params["packs"]
    assert e.params["missing"] == json.dumps(e.params["packs"])
    assert str(e) == "Full suite is not prepared: " + json.dumps(e.params["packs"])

def test_hungarian_demo_needs_localized_jevbench(hu_data):
    with pytest.raises(ArenaError) as info: suites.suite("demo", "hu")
    assert info.value.code == "demo_needs_sources"
    packs.save("hu", "jevbench", fixture_cases("JevBench public", "jevbench", 90), 90)
    cases = suites.suite("demo", "hu")
    assert len(cases) == 120 and [c.id for c in cases[36:]] == [f"hu:jevbench-{i}" for i in range(84)]

def test_hungarian_full_assembles_fixture_packs(hu_data, monkeypatch):
    from arena.i18n import datasets
    packs.save("hu", "jevbench", fixture_cases("JevBench public", "jevbench", 3), 3)
    packs.save("hu", "classification", fixture_cases("Classification", "sst2", 2) + fixture_cases("Classification", "agnews", 2, 10), 4)
    fresh, robust = fixture_cases("Arena Fresh", "fresh", 2), fixture_cases("Robustness", "robustness", 1)
    monkeypatch.setattr(suites, "fresh", lambda split="test", lang="en": fresh)
    monkeypatch.setattr(suites, "robustness", lambda lang="en": robust)
    monkeypatch.setattr(datasets, "expected_counts", lambda lang: {"JevBench public": 3, "Classification": 4, "Arena Fresh": 2, "Robustness": 1})
    cases = suites.suite("full", "hu")
    assert len(cases) == 10 and {c.pack for c in cases} == {"JevBench public", "Classification", "Arena Fresh", "Robustness"}
    monkeypatch.setattr(datasets, "expected_counts", lambda lang: {"JevBench public": 3, "Classification": 5, "Arena Fresh": 2, "Robustness": 1})
    with pytest.raises(ArenaError) as info: suites.suite("full", "hu")
    assert info.value.params["packs"] == {"Classification": {"expected": 5, "available": 4}}
    packs.save("hu", "rag", fixture_cases("RAG relevance", "sst2", 1), 1)  # duplicate id hu:sst2-0
    monkeypatch.setattr(datasets, "expected_counts", lambda lang: {"JevBench public": 3, "Classification": 4, "RAG relevance": 1, "Arena Fresh": 2, "Robustness": 1})
    with pytest.raises(ArenaError) as info: suites.suite("full", "hu")
    assert info.value.code == "duplicate_case_ids"

def test_hungarian_inventory(hu_data):
    packs.save("hu", "classification", fixture_cases("Classification", "sst2", 500), 500)
    inv = suites.inventory("hu")
    assert inv["language"] == "hu" and inv["expected"] == 6871
    slots = {s["slot"]: s for s in inv["slots"]}
    assert slots["abcd"]["source"] == "missing" and not slots["abcd"]["ready"]
    assert slots["abcd"]["reason"] == "separate frozen assessment; Hungarian ABCD is a follow-up"
    assert slots["sst2"] == {**slots["sst2"], "ready": True, "expected": 500, "available": 500}
    assert slots["agnews"]["available"] == 0 and not slots["agnews"]["ready"]
    assert slots["fresh"]["ready"] and slots["fresh"]["expected"] == slots["fresh"]["available"] == 1440
    assert slots["episodes"]["expected"] is None
    assert all(set(s) == {"slot", "pack", "family", "source", "ready", "expected", "available", "licence", "reason"} for s in inv["slots"])
    pk = {p["name"]: p for p in inv["packs"]}
    assert pk["Classification"] == {"name": "Classification", "expected": 1500, "available": 500, "ready": False}
    assert "ABCD next action" not in pk
    assert inv["presets"] == [{"id": "smoke", "count": 36, "ready": True}, {"id": "demo", "count": 120, "ready": False}, {"id": "full", "count": 6871, "ready": False}]
    assert set(suites.inventory()) <= set(inv)

def test_english_suite_and_inventory_unchanged(monkeypatch):
    assert digest([c.model_dump() for c in suites.suite("smoke")]) == "f6f143a706958d3c7009b08a793c143232fb2999d62a3c2e5205f26d4f43e685"
    assert suites.suite("smoke") == suites.suite("smoke", "en")
    monkeypatch.setattr(suites, "jevbench", lambda: [])
    monkeypatch.setattr(suites, "imported", lambda: [])
    inv = suites.inventory()
    assert inv == suites.inventory("en")
    original = ["version", "expected", "available", "packs", "presets", "fresh_status"]
    assert list(inv)[:6] == original and list(inv)[6:] == ["language", "slots"]
    counts = {"Arena Fresh": 1440, "Robustness": 1000}
    assert {k: inv[k] for k in original} == {
        "version": "arena-v2", "expected": 7671, "available": 2440,
        "packs": [{"name": k, "expected": v, "available": counts.get(k, 0), "ready": counts.get(k, 0) == v} for k, v in suites.EXPECTED.items()],
        "presets": [{"id": "smoke", "count": 36, "ready": True}, {"id": "demo", "count": 120, "ready": False}, {"id": "full", "count": 7671, "ready": False}],
        "fresh_status": "Executable-policy fixtures v2: new seed, explicit routing and approval rules. Human semantic audit not claimed."}
    assert inv["language"] == "en"
    slots = {s["slot"]: s for s in inv["slots"]}
    assert slots["sst2"] == {**slots["sst2"], "expected": 500, "available": 0, "ready": False}
    assert slots["fresh"]["available"] == 1440 and slots["fresh"]["ready"]

def test_english_slots_counted_by_family(monkeypatch):
    def cases(pack, family, n, prefix):
        base = smoke()[0]
        return [base.model_copy(deep=True, update={"id": f"{prefix}-{i}", "pack": pack, "family": family, "provenance": {}}) for i in range(n)]
    monkeypatch.setattr(suites, "jevbench", lambda: cases("JevBench public", "triage", 231, "jb"))
    monkeypatch.setattr(suites, "imported", lambda: cases("Classification", "SST-2", 500, "sst") + cases("Classification", "AG News", 3, "ag")
                        + cases("Multilingual", "XNLI", 500, "x") + cases("Typed decisions", "refund", 7, "ty") + cases("Typed decisions", "ship", 5, "ty2"))
    slots = {s["slot"]: s for s in suites.inventory()["slots"]}
    assert (slots["jevbench"]["available"], slots["jevbench"]["ready"]) == (231, True)
    assert (slots["sst2"]["available"], slots["sst2"]["ready"]) == (500, True)
    assert (slots["agnews"]["available"], slots["banking77"]["available"]) == (3, 0)
    assert (slots["xnli"]["available"], slots["xnli"]["expected"], slots["xnli"]["ready"]) == (500, 500, True)
    assert slots["massive"]["available"] == 0 and slots["typed-decisions"]["available"] == 12
    assert slots["abcd"]["expected"] is None and not slots["abcd"]["ready"]
    assert slots["episodes"]["ready"] and slots["episodes"]["available"] is None

def test_language_without_datasets_config_is_all_missing(tmp_path, monkeypatch):
    import shutil
    from arena.i18n import datasets
    from arena.config import ROOT
    (tmp_path / "en").mkdir(); shutil.copy(ROOT / "locales" / "en" / "datasets.yaml", tmp_path / "en" / "datasets.yaml")
    monkeypatch.setattr(datasets, "LOCALES", tmp_path)
    monkeypatch.setattr(packs, "DATASETS", tmp_path / "datasets")
    inv = suites.inventory("xx")
    assert inv["language"] == "xx" and inv["expected"] == 0 and inv["packs"] == []
    assert inv["slots"] and all(s["source"] == "missing" and s["reason"] == "no datasets.yaml" and not s["ready"] for s in inv["slots"])
    assert {p["id"]: p["ready"] for p in inv["presets"]} == {"smoke": False, "demo": False, "full": False}

@pytest.fixture
def arena(tmp_path, monkeypatch):
    runs = tmp_path / "runs"; runs.mkdir()
    monkeypatch.setattr(module, "RUNS", runs); monkeypatch.setattr(module, "DATA", tmp_path)
    ctl = module.Controller(Store(tmp_path / "store.db"))
    async def readiness(): return {"models": [{"id": "uniform", "name": "Uniform baseline", "ready": True}], "hardware": {}, "judge": {"ready": True}}
    ctl.readiness = readiness
    class Worker:
        def __init__(self, mid, folder, cancel): self.id = mid; self.folder = folder; self.cancel = cancel; self.meta = {}; self.dead = False; self.cost = 0; self.reserved = 0
        async def load(self): self.folder.mkdir(parents=True, exist_ok=True)
        async def predict(self, case, cap):
            await asyncio.sleep(.003)
            if self.cancel.is_set(): raise asyncio.CancelledError()
            return Prediction(case_id=case.id, model_id=self.id, status="ok", selected=case.question.labels[0], request_ms=3)
        async def unload(self): return {"container_stopped": True, "memory_within_baseline": True}
    monkeypatch.setattr(module, "Adapter", Worker)
    return ctl

async def test_hungarian_run_records_language_and_resumes(arena):
    settings.set_language("hu")
    ctl = arena
    rid = await ctl.start(RunRequest(model_ids=["uniform"], preset="smoke", judge=False, idempotency_key="hu-smoke"))
    manifest = ctl.store.run(rid)["manifest"]
    assert manifest["language"] == "hu" and manifest["case_count"] == 36
    assert all(c.language == "hu" for c in ctl.cases(rid))
    for _ in range(500):
        if len(ctl.store.predictions(rid)) >= 2: break
        await asyncio.sleep(.002)
    ctl.cancel(rid); await ctl.tasks[rid]
    await ctl.resume(rid); await ctl.tasks[rid]
    assert ctl.store.run(rid)["status"] == "complete" and len(ctl.store.predictions(rid)) == 36

async def test_english_run_records_language(arena):
    ctl = arena
    rid = await ctl.start(RunRequest(model_ids=["uniform"], preset="smoke", judge=False, idempotency_key="en-smoke"))
    await ctl.tasks[rid]
    assert ctl.store.run(rid)["manifest"]["language"] == "en"
    assert digest([c.model_dump() for c in ctl.cases(rid)]) == "f6f143a706958d3c7009b08a793c143232fb2999d62a3c2e5205f26d4f43e685"

def test_setup_prepares_selected_language(monkeypatch):
    from arena import setup, importers, source_fetch
    calls = []
    monkeypatch.setattr(source_fetch, "REPOS", {})
    monkeypatch.setattr(importers, "prepare_all", lambda: calls.append("en"))
    def prepare_language(lang, progress=None, only=None):
        calls.append(lang); progress("banking77: failed, skipped (EngineError: x)"); return {}
    monkeypatch.setattr(packs, "prepare_language", prepare_language)
    messages = []
    done = "Preparation complete. Run Smoke before the full comparison."
    setup.prepare([], messages.append, models=False, workers=False)
    assert calls == ["en"] and messages[-1] == done
    settings.set_language("hu")
    setup.prepare([], messages.append, models=False, workers=False)
    assert calls == ["en", "en", "hu"] and "banking77: failed, skipped (EngineError: x)" in messages
    assert messages[-1] == "Preparation complete; Hungarian data incomplete: banking77. Run Smoke before the full comparison."
    def complete(lang, progress=None, only=None): progress("fresh: generated on demand"); progress("sst2: 500 cases"); return {}
    monkeypatch.setattr(packs, "prepare_language", complete)
    setup.prepare([], messages.append, models=False, workers=False)
    assert messages[-1] == done
    def broken(lang, progress=None, only=None): raise RuntimeError("network down")
    monkeypatch.setattr(packs, "prepare_language", broken)
    setup.prepare([], messages.append, models=False, workers=False)
    assert messages[-1] == "Preparation complete; Hungarian data incomplete: RuntimeError: network down. Run Smoke before the full comparison."
