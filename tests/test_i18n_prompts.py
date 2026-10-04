import json
import re
import pytest
import yaml
from arena import episodes, fresh
from arena.config import ROOT
from arena.i18n import check, prompts
from arena.i18n.check import Issue
from arena.i18n.prompts import has_language, labels, prompt

META = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}

def write(root, code, data, ui=None):
    d = root / code; d.mkdir(parents=True, exist_ok=True)
    (d / "locale.json").write_text(json.dumps({"code": code, **META}), encoding="utf-8")
    (d / "ui.json").write_text(json.dumps(ui or {"a": "A"}), encoding="utf-8")
    if data is not None: (d / "prompts.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

@pytest.fixture
def tmp_locales(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts, "LOCALES", tmp_path)
    return tmp_path

# --- loader -----------------------------------------------------------------

def test_rubric_is_exact_english():
    assert prompt("en", "fresh.rubric") == "Apply only the explicit policy and evidence in the state."

def test_missing_key_raises_keyerror_with_lang_and_key():
    with pytest.raises(KeyError, match="en:fresh.nope"): prompt("en", "fresh.nope")

def test_missing_language_raises_keyerror(tmp_locales):
    write(tmp_locales, "en", {"a": "A"})
    with pytest.raises(KeyError, match="xx:a"): prompt("xx", "a")

def test_empty_and_non_leaf_values_raise(tmp_locales):
    write(tmp_locales, "xx", {"a": "", "g": {"b": "B"}})
    with pytest.raises(KeyError, match="xx:a"): prompt("xx", "a")
    with pytest.raises(KeyError, match="xx:g"): prompt("xx", "g")
    assert prompt("xx", "g.b") == "B"

def test_format_params_are_applied(tmp_locales):
    write(tmp_locales, "xx", {"t": "Hi {name}, {{literal}}"})
    assert prompt("xx", "t", name="Ann") == "Hi Ann, {literal}"

def test_loader_resolves_locales_at_call_time(tmp_locales):
    write(tmp_locales, "en", {"rubric": "patched"})
    assert prompt("en", "rubric") == "patched"

def test_labels_en_values_equal_ids():
    assert labels("en", "directions") == {"north": "north", "east": "east", "south": "south", "west": "west"}
    en = yaml.safe_load((ROOT / "locales" / "en" / "prompts.yaml").read_text(encoding="utf-8"))
    for group in en["labels"]: assert all(k == v for k, v in labels("en", group).items()), group

def test_labels_missing_group_or_empty_value_raises(tmp_locales):
    write(tmp_locales, "xx", {"labels": {"g": {"a": "A", "b": ""}}})
    with pytest.raises(KeyError, match="xx:labels.h"): labels("xx", "h")
    with pytest.raises(KeyError, match="xx:labels.g.b"): labels("xx", "g")

def test_has_language(tmp_locales):
    write(tmp_locales, "en", {"a": "A"}); write(tmp_locales, "xx", None)
    assert has_language("en") and not has_language("xx") and not has_language("zz")

def test_repo_en_has_no_unquoted_yaml_booleans():
    def walk(node):
        assert isinstance(node, (dict, str)), node
        if isinstance(node, dict):
            for k, v in node.items(): assert isinstance(k, str), k; walk(v)
    walk(yaml.safe_load((ROOT / "locales" / "en" / "prompts.yaml").read_text(encoding="utf-8")))

# --- reference copies stay in sync with the English importers ---------------

def _source(name): return (ROOT / "arena" / name).read_text(encoding="utf-8")

@pytest.mark.parametrize("key", ["sst2", "agnews", "banking77", "xnli", "massive", "scifact"])
def test_importer_questions_match_source(key):
    text = prompt("en", f"importers.{key}")
    files = _source("importers.py") + _source("multilingual.py")
    assert re.search(r"[\"']" + re.escape(text) + r"[\"']", files), text

def test_importer_state_templates_match_source():
    scifact = prompt("en", "importers.scifact_state", claim="{query}", title="{doc['title']}", text="{doc['text']}")
    xnli = prompt("en", "importers.xnli_state", premise="{row['premise'][lang]}", hypothesis="{hyp[lang]}")
    source = _source("importers.py")
    assert 'f"' + scifact.replace("\n", "\\n") + '"' in source
    assert 'f"' + xnli.replace("\n", "\\n") + '"' in source

# --- en templates rebuild the generators' English strings exactly -----------

def _yes(x): return prompt("en", "fresh.yes") if x else prompt("en", "fresh.no")

def _fresh_state(family, index, split, proof):
    a, b, c, n = proof["a"], proof["b"], proof["c"], proof["n"]
    entity = f"{prompt('en', f'fresh.split_entity.{split}')}-{family+1}-{index+1:03}"
    p = lambda k, **kw: prompt("en", f"fresh.family{family}.{k}", **kw)
    if family == 0:
        topic = p("topics.payment") if a else (p("topics.outage") if b else p("topics.onboarding"))
        state = p("state", entity=entity, topic=topic, unavailable=_yes(c), n=n)
    elif family == 1: state = p("state", entity=entity, eligible=_yes(a), approved=_yes(b), n=n)
    elif family == 2:
        opened, closed = p("status.opened"), p("status.closed")
        stated = opened if a else closed
        claim = stated if b else (closed if a else opened)
        state = p("state", entity=entity, stated=stated, claim=claim, n=n)
    elif family == 3: state = p("state", entity=entity, desired=p("access.write") if a else p("access.read"), approval=_yes(b))
    elif family == 4: state = p("state", entity=entity, confidential=_yes(a), signed=_yes(b), n=n)
    elif family == 5:
        atlas, boreal = p("products.Atlas"), p("products.Boreal")
        product = atlas if a else boreal
        state = p("state", entity=entity, product=product, docproduct=product if b else (boreal if a else atlas), n=n)
    elif family == 6:
        active, inactive = p("status.active"), p("status.inactive")
        rec1 = active if a else inactive
        state = p("state", entity=entity, rec1=rec1, rec2=rec1 if b else (inactive if a else active))
    else: state = p("state", entity=entity, data_loss=_yes(a), degraded=_yes(b), notified=_yes(c))
    pres = lambda k: prompt("en", f"fresh.presentation.{k}")
    if split == "dev": state = pres("dev_prefix") + state.replace(pres("policy_word"), pres("dev_policy_word"))
    if split == "calibration": state = pres("calibration_prefix") + state.replace(pres("policy_word"), pres("calibration_policy_word"))
    return state

@pytest.mark.parametrize("split", ["test", "dev", "calibration"])
@pytest.mark.parametrize("family", range(8))
def test_fresh_templates_rebuild_english(family, split):
    for index in range(6):
        cases = fresh.scenario(family, index, split)
        assert _fresh_state(family, index, split, cases[0].provenance["proof"]) == cases[0].state
        for case in cases:
            name = {"choice": "choice", "noul": "binary", "score": "ordinal"}[case.question.kind]
            assert prompt("en", f"fresh.family{family}.{name}") == case.question.text
            assert prompt("en", "fresh.rubric") == case.question.rubric
            if case.question.kind == "choice":
                assert labels("en", "fresh_choice").keys() >= set(case.question.labels)

def test_robustness_strings_rebuild_english():
    variants = {c.variant: c for c in fresh.robustness()[:5]}
    anchor = fresh.scenario(0, 0)[0]
    assert variants["paraphrase"].question.text == prompt("en", "robustness.paraphrase_prefix") + anchor.question.text
    assert variants["distractor"].state == anchor.state + prompt("en", "robustness.distractor")
    assert variants["injection"].state == anchor.state + prompt("en", "robustness.injection")

def test_episode_templates_rebuild_english():
    w = episodes.Warehouse(5090); case = w.case()
    assert case.state == prompt("en", "episodes.warehouse_state", pos=w.pos, goal=w.goal, blocked=sorted(w.blocked))
    assert case.question.text == prompt("en", "episodes.warehouse_question")
    assert set(case.question.labels) == set(labels("en", "directions"))
    t = episodes.Tickets(5091)
    for _ in range(12):
        case = t.case(); cur = t.current
        topic = prompt("en", "episodes.ticket_topics." + cur["topic"])
        assert case.state == prompt("en", "episodes.tickets_state", seed=5091, step=t.steps, topic=topic, restricted=_yes(cur["restricted"]))
        assert case.question.text == prompt("en", "episodes.tickets_question")
        assert case.question.labels == list(labels("en", "ticket_queues"))
        t.steps += 1

# --- checker ----------------------------------------------------------------

EN = {"t": "Hi {name}", "u": "Plain", "labels": {"g": {"a": "a", "b": "b"}}}

def test_clean_prompts_have_no_issues(tmp_path):
    write(tmp_path, "en", EN)
    write(tmp_path, "xx", {"t": "Szia {name}", "u": "Sima", "labels": {"g": {"a": "A", "b": "B"}}})
    assert check.check("xx", tmp_path) == []
    assert check.summary("xx", tmp_path) == ["xx ui.json: 100.0% complete (0 missing)", "xx prompts.yaml: 100.0% complete (0 missing)"]

def test_prompt_placeholder_mismatch_and_extra_key_are_errors(tmp_path):
    write(tmp_path, "en", EN)
    write(tmp_path, "xx", {"t": "Szia {nev}", "u": "Sima {{x}}", "z": "x", "labels": {"g": {"a": "A", "b": "B"}}})
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "prompts.yaml", "t", "placeholders ['nev'] != en ['name']"),
        Issue("error", "xx", "prompts.yaml", "z", "key not in en"),
    ]

def test_missing_prompt_key_is_error_and_empty_is_warning(tmp_path):
    write(tmp_path, "en", EN)
    write(tmp_path, "xx", {"t": "", "labels": {"g": {"a": "A", "b": "B"}}})
    assert check.check("xx", tmp_path) == [
        Issue("warning", "xx", "prompts.yaml", "t", "empty (test data generation would fail)"),
        Issue("error", "xx", "prompts.yaml", "u", "missing (test data generation would fail)"),
    ]
    assert check.summary("xx", tmp_path)[1] == "xx prompts.yaml: 50.0% complete (2 missing)"

def test_duplicate_localized_labels_are_errors(tmp_path):
    write(tmp_path, "en", EN)
    write(tmp_path, "xx", {"t": "{name}", "u": "U", "labels": {"g": {"a": "X", "b": "X"}}})
    assert check.check("xx", tmp_path) == [Issue("error", "xx", "prompts.yaml", "labels.g", "duplicate localized labels ['X']")]

def test_label_ids_must_equal_en_ids(tmp_path):
    write(tmp_path, "en", EN)
    write(tmp_path, "xx", {"t": "{name}", "u": "U", "labels": {"g": {"a": "A", "c": "C"}}})
    assert check.check("xx", tmp_path) == [Issue("error", "xx", "prompts.yaml", "labels.g", "label ids differ from en: missing ['b'], extra ['c']")]

def test_locale_without_prompts_is_warning_only_when_en_has_them(tmp_path):
    write(tmp_path, "en", None); write(tmp_path, "xx", None)
    assert check.check("xx", tmp_path) == [] and check.summary("xx", tmp_path) == ["xx ui.json: 100.0% complete (0 missing)"]
    write(tmp_path, "en", EN)
    assert check.check("xx", tmp_path) == [Issue("warning", "xx", "prompts.yaml", "", "prompts.yaml missing (test data unavailable in this language)")]
    assert check.summary("xx", tmp_path)[1] == "xx prompts.yaml: 0.0% complete (4 missing)"

def test_unreadable_or_non_mapping_prompts_are_errors(tmp_path):
    write(tmp_path, "en", EN); write(tmp_path, "xx", None)
    (tmp_path / "xx" / "prompts.yaml").write_text("a: [unclosed", encoding="utf-8")
    issues = check.check("xx", tmp_path)
    assert len(issues) == 1 and issues[0].level == "error" and issues[0].message.startswith("cannot read catalog")
    (tmp_path / "xx" / "prompts.yaml").write_text("- 1\n", encoding="utf-8")
    assert check.check("xx", tmp_path) == [Issue("error", "xx", "prompts.yaml", "", "catalog must be a mapping")]

def test_unquoted_boolean_and_bad_format_are_errors(tmp_path):
    write(tmp_path, "en", EN)
    (tmp_path / "xx").mkdir(exist_ok=True)
    write(tmp_path, "xx", None)
    (tmp_path / "xx" / "prompts.yaml").write_text('t: "{name"\nu: yes\nlabels: {g: {a: A, b: B}}\n', encoding="utf-8")
    assert check.check("xx", tmp_path) == [
        Issue("error", "xx", "prompts.yaml", "t", "invalid format string: expected '}' before end of string"),
        Issue("error", "xx", "prompts.yaml", "u", "value must be a string"),
    ]

def test_new_language_scaffolds_blank_prompts(tmp_path):
    write(tmp_path, "en", EN)
    check.new_language("xx", "Example", "Exemplum", tmp_path)
    data = yaml.safe_load((tmp_path / "xx" / "prompts.yaml").read_text(encoding="utf-8"))
    assert data == {"t": "", "u": "", "labels": {"g": {"a": "", "b": ""}}}
    assert [i for i in check.check("xx", tmp_path) if i.file == "prompts.yaml"] == [
        Issue("warning", "xx", "prompts.yaml", k, "empty (test data generation would fail)") for k in ("t", "u", "labels.g.a", "labels.g.b")]

def test_new_language_without_en_prompts_scaffolds_none(tmp_path):
    write(tmp_path, "en", None)
    check.new_language("xx", "Example", "Exemplum", tmp_path)
    assert not (tmp_path / "xx" / "prompts.yaml").exists()

def test_unreadable_en_prompts_is_error(tmp_path):
    write(tmp_path, "en", None); write(tmp_path, "xx", EN)
    (tmp_path / "en" / "prompts.yaml").write_text("- 1\n", encoding="utf-8")
    assert check.check("xx", tmp_path) == [Issue("error", "xx", "prompts.yaml", "", "en catalog must be a mapping")]
    assert check.summary("xx", tmp_path) == ["xx ui.json: 100.0% complete (0 missing)"]
