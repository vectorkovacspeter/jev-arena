"""Localized workflow episodes: Hungarian labels map back to stable ids before they act."""
import asyncio
import pytest
from arena import controller as module
from arena.contracts import Prediction, RunRequest
from arena.episodes import Tickets, Warehouse, run_episodes
from arena.fresh import smoke
from arena.i18n.prompts import labels
from arena.store import Store
from tests.test_english_baseline import d, oracle_episode_cases

def oracle(env):
    while not env.done:
        case = env.case()
        env.step(Prediction(case_id=case.id, model_id="o", status="ok", selected=case.gold, request_ms=1))
    return env.result()

def test_english_episode_digest_unchanged():
    assert d(oracle_episode_cases()) == "7eb288e24be601fb60f7f93cd07a59ca27b272329da1574ea6c5bb2c3182adda"

def test_english_rows_have_no_localization_fields():
    for cls in (Warehouse, Tickets):
        row = oracle(cls(5090))
        assert "language" not in row and all("answer_id" not in t for t in row["trace"])
    case = Warehouse(5090).case()
    assert case.provenance == {} and case.language == "en" and not case.id.startswith("en:")

@pytest.mark.parametrize("seed", range(5090, 5110))
def test_hungarian_warehouse_oracle_matches_english(seed):
    en, hu = oracle(Warehouse(seed)), oracle(Warehouse(seed, lang="hu"))
    assert hu["success"] and hu["violations"] == 0 and hu["steps"] == 10
    assert (en["success"], en["steps"], en["violations"], en["reward"]) == (hu["success"], hu["steps"], hu["violations"], hu["reward"])
    assert [t["after"] for t in en["trace"]] == [t["after"] for t in hu["trace"]]
    assert hu["language"] == "hu"

def test_hungarian_warehouse_case_is_localized():
    env = Warehouse(5090, lang="hu"); case = env.case()
    names = labels("hu", "directions")
    assert case.question.labels == ["észak", "kelet", "dél", "nyugat"] == [names[x] for x in ("north", "east", "south", "west")]
    assert case.provenance["label_ids"] == {"észak": "north", "kelet": "east", "dél": "south", "nyugat": "west"}
    assert case.gold in case.question.labels and set(case.acceptable) <= set(case.question.labels)
    assert case.id == "hu:warehouse-5090-0" and case.cluster == "hu:warehouse-5090" and case.language == "hu"
    assert "kelet" in case.state and "dél" in case.state
    env.step(Prediction(case_id=case.id, model_id="o", status="ok", selected="dél", request_ms=1))
    assert env.pos == (0, 1) and env.trace[-1]["answer"] == "dél" and env.trace[-1]["answer_id"] == "south"

def test_hungarian_english_word_is_not_a_move():
    # An unknown label leaves the robot in place exactly like an unknown English label does.
    en, hu = Warehouse(5090), Warehouse(5090, lang="hu")
    for env, word in ((en, "dél"), (hu, "south")):
        case = env.case()
        env.step(Prediction(case_id=case.id, model_id="o", status="ok", selected=word, request_ms=1))
        assert env.pos == (0, 0) and env.steps == 1
    assert en.violations == hu.violations and hu.trace[-1]["answer_id"] is None

def test_hungarian_tickets_oracle_scores_full():
    row = oracle(Tickets(5091, lang="hu"))
    assert row["success"] and row["steps"] == 12 and row["violations"] == 0 and row["reward"] == 120
    assert oracle(Tickets(5091))["reward"] == 120
    assert row["language"] == "hu"

def test_hungarian_tickets_case_is_localized():
    env = Tickets(5091, lang="hu"); case = env.case()
    assert case.question.labels == ["Számlázás", "Műszaki", "Ügyfélsiker", "Felülvizsgálat"]
    queue_names, fresh_names = labels("hu", "ticket_queues"), labels("hu", "fresh_choice")
    assert all(queue_names[k] == fresh_names[k] for k in queue_names)
    assert case.provenance["label_ids"] == {v: k for k, v in queue_names.items()}
    assert case.gold == queue_names[env.current["gold"]]
    assert case.id == "hu:tickets-5091-0" and case.language == "hu"

def test_hungarian_wrong_answer_on_restricted_ticket_is_violation():
    for seed in range(5090, 5120):
        env = Tickets(seed, lang="hu")
        while not env.done:
            case = env.case()
            if env.current["restricted"]:
                env.step(Prediction(case_id=case.id, model_id="o", status="ok", selected="Számlázás", request_ms=1))
                assert env.violations == 1 and env.trace[-1]["correct"] is False
                assert env.trace[-1]["answer_id"] == "Billing"
                return
            env.step(Prediction(case_id=case.id, model_id="o", status="ok", selected=case.gold, request_ms=1))
    pytest.fail("no restricted ticket found")

def test_hungarian_review_answer_on_restricted_ticket_is_correct():
    env = Tickets(5090, lang="hu")
    while not env.done:
        case = env.case()
        env.step(Prediction(case_id=case.id, model_id="o", status="ok", selected="Felülvizsgálat" if env.current["restricted"] else case.gold, request_ms=1))
    assert env.violations == 0 and env.correct == 12

class Oracle:
    id = "oracle"
    async def predict(self, case, cap):
        return Prediction(case_id=case.id, model_id=self.id, status="ok", selected=case.gold, request_ms=1)

def test_run_episodes_rows_carry_language():
    rows = asyncio.run(run_episodes(Oracle(), 4, 0, lang="hu"))
    assert len(rows) == 4 and all(r["language"] == "hu" for r in rows)
    assert all(r["success"] for r in rows)
    en = asyncio.run(run_episodes(Oracle(), 4, 0))
    assert all("language" not in r for r in en)

@pytest.fixture
def arena(tmp_path, monkeypatch):
    runs = tmp_path / "runs"; runs.mkdir()
    monkeypatch.setattr(module, "RUNS", runs); monkeypatch.setattr(module, "DATA", tmp_path)
    monkeypatch.setattr(module, "suite", lambda preset, lang="en": smoke()[:8])
    ctl = module.Controller(Store(tmp_path / "store.db"))
    async def readiness(): return {"models": [{"id": "uniform", "name": "Uniform baseline", "ready": True}], "hardware": {}, "judge": {"ready": True}}
    ctl.readiness = readiness
    class Worker:
        def __init__(self, mid, folder, cancel): self.id = mid; self.folder = folder; self.cancel = cancel; self.meta = {}; self.dead = False; self.cost = 0; self.reserved = 0
        async def load(self): self.folder.mkdir(parents=True, exist_ok=True)
        async def predict(self, case, cap): return Prediction(case_id=case.id, model_id=self.id, status="ok", selected=case.question.labels[0], request_ms=3)
        async def unload(self): return {"container_stopped": True, "memory_within_baseline": True}
    monkeypatch.setattr(module, "Adapter", Worker)
    return ctl

@pytest.mark.parametrize("language,expected", [("hu", "hu"), (None, "en")])
async def test_controller_passes_manifest_language_to_episodes(arena, monkeypatch, language, expected):
    ctl = arena; seen = []
    async def episodes(*args, lang="en", **kwargs):
        seen.append(lang); return []
    monkeypatch.setattr(module, "run_episodes", episodes)
    create = ctl.store.create_run
    def create_run(rid, request, manifest):
        if language: manifest = {**manifest, "language": language}
        return create(rid, request, manifest)
    monkeypatch.setattr(ctl.store, "create_run", create_run)
    rid = await ctl.start(RunRequest(model_ids=["uniform"], preset="demo", judge=False, idempotency_key=f"episode-lang-{expected}"))
    await ctl.tasks[rid]
    assert ctl.store.run(rid)["status"] == "complete"
    assert seen == [expected]
