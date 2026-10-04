"""Localized Arena Fresh, Robustness and Smoke: same proofs and golds, localized text."""
import pytest
from arena import fresh
from arena.i18n.prompts import labels, prompt

ENGLISH_POLICY_WORDS = ("Policy:", "route solely", "Ticket ", "goes to")

@pytest.fixture(scope="module")
def en(): return fresh.fresh()

@pytest.fixture(scope="module")
def hu(): return fresh.fresh(lang="hu")

def stable_gold(case):
    """English-id gold: choice golds map back through label_ids; noul/score golds are already ids."""
    return case.provenance["label_ids"][case.gold] if case.question.kind == "choice" else case.gold

def test_hu_fresh_count_ids_and_language(en, hu):
    assert len(hu) == len(en) == 1440
    assert all(c.id.startswith("hu:") and c.cluster.startswith("hu:") and c.language == "hu" for c in hu)
    assert [c.id for c in hu] == ["hu:" + c.id for c in en]
    assert [c.cluster for c in hu] == ["hu:" + c.cluster for c in en]

def test_hu_metadata_stays_english(en, hu):
    for e, h in zip(en, hu):
        assert (h.pack, h.family, h.split, h.question.kind, h.question.id) == (e.pack, e.family, e.split, e.question.kind, e.question.id)
        assert h.provenance["proof"] == e.provenance["proof"]

@pytest.mark.parametrize("split", ["test", "dev", "calibration"])
def test_hu_golds_equal_english_after_mapping(split):
    en_cases, hu_cases = fresh.fresh(split), fresh.fresh(split, lang="hu")
    assert len(en_cases) == len(hu_cases)
    for e, h in zip(en_cases, hu_cases):
        assert stable_gold(h) == e.gold, h.id
        if h.question.kind == "choice":
            assert [h.provenance["label_ids"][x] for x in h.question.labels] == e.question.labels
            assert h.question.labels == [labels("hu", "fresh_choice")[x] for x in e.question.labels]
        else:
            assert h.question.labels == e.question.labels  # protocol ids: no/yes and 0..4
            assert "label_ids" not in h.provenance

def test_all_three_kinds_are_covered(hu):
    assert {c.question.kind for c in hu} == {"choice", "noul", "score"}

def test_hu_choice_labels_unique_and_gold_in_labels(hu):
    for c in hu:
        assert len(set(c.question.labels)) == len(c.question.labels)
        assert c.gold in c.question.labels
        if c.question.kind == "choice":
            assert set(c.provenance["label_ids"]) == set(c.question.labels)

def test_hu_fresh_choice_labels_unique_globally():
    values = list(labels("hu", "fresh_choice").values())
    assert len(set(values)) == len(values)
    assert set(labels("hu", "fresh_choice")) == set(labels("en", "fresh_choice"))

@pytest.mark.parametrize("split", ["test", "dev", "calibration"])
def test_no_english_policy_keywords_in_hu_states(split):
    for c in fresh.fresh(split, lang="hu"):
        for word in ENGLISH_POLICY_WORDS: assert word not in c.state, (c.id, word)

def test_hu_question_texts_and_rubric_are_localized(en, hu):
    for e, h in zip(en, hu):
        assert h.question.text != e.question.text
        assert h.question.rubric == prompt("hu", "fresh.rubric") != e.question.rubric

@pytest.mark.parametrize("family", range(8))
def test_hu_policy_labels_appear_verbatim(family):
    hu_labels = labels("hu", "fresh_choice")
    state = fresh.scenario(family, 0, lang="hu")[0].state
    named = {0: ["Billing", "Engineering", "Success"], 1: ["Proceed", "Review", "Stop"], 2: ["Supported", "Contradicted"],
             3: ["Reader", "Editor", "Request approval"], 4: ["Secure review", "Intake", "Archive"], 5: ["Relevant"],
             6: ["Unknown"], 7: ["Critical", "Warning", "Healthy"]}[family]
    for label_id in named: assert hu_labels[label_id] in state, (family, label_id)

def test_hu_dev_and_calibration_presentation():
    dev = fresh.scenario(0, 0, "dev", lang="hu")[0].state
    cal = fresh.scenario(0, 0, "calibration", lang="hu")[0].state
    test = fresh.scenario(0, 0, lang="hu")[0].state
    p = lambda k: prompt("hu", f"fresh.presentation.{k}")
    assert p("policy_word") in test
    assert dev.startswith(p("dev_prefix")) and p("dev_policy_word") in dev and p("policy_word") not in dev
    assert cal.startswith(p("calibration_prefix")) and p("calibration_policy_word") in cal and p("policy_word") not in cal

def test_family6_gold_uses_stable_label_not_title_case():
    for index in range(30):
        cases = fresh.scenario(6, index, lang="hu")
        en_choice = fresh.scenario(6, index)[0]
        assert cases[0].gold == labels("hu", "fresh_choice")[en_choice.gold]

def test_english_has_no_label_ids_and_no_prefix(en):
    assert all("label_ids" not in c.provenance and not c.id.startswith("en:") and c.language == "en" for c in en)

def test_unknown_language_raises():
    with pytest.raises(KeyError, match="zz:"): fresh.scenario(0, 0, lang="zz")

# --- robustness and smoke ---------------------------------------------------

@pytest.fixture(scope="module")
def rob():
    return fresh.robustness(), fresh.robustness(lang="hu")

def test_hu_robustness_lines_up_with_english(rob):
    en_cases, hu_cases = rob
    assert len(hu_cases) == len(en_cases) == 1000
    for e, h in zip(en_cases, hu_cases):
        assert h.id == "hu:" + e.id and h.variant == e.variant and h.pack == e.pack == "Robustness"
        assert h.language == "hu" and h.provenance["anchor_id"] == "hu:" + e.provenance["anchor_id"]
        assert h.provenance["label_ids"][h.gold] == e.gold
        assert [h.provenance["label_ids"][x] for x in h.question.labels] == e.question.labels
        assert h.provenance.get("counterfactual_source_index") == e.provenance.get("counterfactual_source_index")
        assert h.provenance.get("paraphrase_status") == e.provenance.get("paraphrase_status")

def test_hu_robustness_variant_texts(rob):
    _, hu_cases = rob
    by = {c.variant: c for c in hu_cases[:5]}
    anchor = fresh.scenario(0, 0, lang="hu")[0]
    assert by["reversed_options"].question.labels == list(reversed(anchor.question.labels))
    assert by["paraphrase"].question.text == prompt("hu", "robustness.paraphrase_prefix") + anchor.question.text
    assert by["distractor"].state == anchor.state + prompt("hu", "robustness.distractor")
    assert by["injection"].state == anchor.state + prompt("hu", "robustness.injection")
    assert "Hagyd figyelmen kívül" in by["injection"].state and "Ignore every rule" not in by["injection"].state
    cf = by["counterfactual"]
    source = fresh.scenario(0, cf.provenance["counterfactual_source_index"], lang="hu")[0]
    assert cf.state == source.state and cf.gold == source.gold != anchor.gold

def test_hu_robustness_has_no_english_text(rob):
    _, hu_cases = rob
    for c in hu_cases:
        for word in ENGLISH_POLICY_WORDS + ("Unrelated warehouse memo", "Using the stated rules"):
            assert word not in c.state and word not in c.question.text, (c.id, word)

def test_hu_smoke():
    en_cases, hu_cases = fresh.smoke(), fresh.smoke(lang="hu")
    assert len(hu_cases) == len(en_cases) == 36
    assert [c.id for c in hu_cases] == ["hu:" + c.id for c in en_cases]
    assert all(stable_gold(h) == e.gold for e, h in zip(en_cases, hu_cases))
