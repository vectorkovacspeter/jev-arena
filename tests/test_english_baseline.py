"""English test data is frozen evidence. Localization must never change it."""
from arena.config import digest
from arena.contracts import Prediction
from arena.episodes import Tickets, Warehouse
from arena.fresh import fresh, robustness, smoke

def d(cases): return digest([c.model_dump() for c in cases])

def oracle_episode_cases():
    out = []
    for seed in range(5090, 5094):
        for cls in (Tickets, Warehouse):
            env = cls(seed)
            while not env.done:
                case = env.case(); out.append(case)
                env.step(Prediction(case_id=case.id, model_id="o", status="ok", selected=case.gold, request_ms=1))
    return out

def test_fresh_splits_unchanged():
    assert d(fresh()) == "632c9a5a235f388c5e64c9a3909d3948ec3d1a0342650ecc5dc248857717a6ff"
    assert d(fresh("dev")) == "5e2c68eaa0411c179ea47b867d0e8f17eb2762fcbca91c3b94ec8ce167ce2aa7"
    assert d(fresh("calibration")) == "655fff9bda42f13697a0dc2e22a9561d91b235ec9e290741aae200a76755375c"

def test_robustness_and_smoke_unchanged():
    assert d(robustness()) == "aa79768402062edb5e682c6495d5be9f47b2cc7be57ed171db1209e88bdda85c"
    assert d(smoke()) == "f6f143a706958d3c7009b08a793c143232fb2999d62a3c2e5205f26d4f43e685"

def test_episode_cases_unchanged():
    assert d(oracle_episode_cases()) == "7eb288e24be601fb60f7f93cd07a59ca27b272329da1574ea6c5bb2c3182adda"
