"""Dataset slot schema (datasets.yaml), the config-driven native importer and per-language packs. Offline."""
import json
import random
from collections import Counter
from pathlib import Path
import pytest
import yaml
from pydantic import ValidationError
from arena import importers, suites
from arena.contracts import Case
from arena.i18n import check, datasets, native, packs
from arena.i18n.datasets import Slot
from arena.i18n.prompts import labels

FIXTURES = Path(__file__).parent / "fixtures" / "i18n"

@pytest.fixture
def offline(monkeypatch, tmp_path):
    """Downloads resolve to the committed fixtures; packs are written under tmp_path."""
    calls = []
    def fake_download(repo, filename, **kw):
        calls.append((repo, filename, kw))
        return str(FIXTURES / filename)
    monkeypatch.setattr(native, "hf_hub_download", fake_download)
    monkeypatch.setattr(native, "DATASETS", tmp_path)
    monkeypatch.setattr(packs, "DATASETS", tmp_path)
    return calls

def sentiment_slot(**kw):
    return Slot(**{"source": "native", "pack": "Classification", "family": "HuSST", "repo": "NYTK/HuSST", "revision": "abc123",
                   "files": ["sentiment.parquet"], "fields": {"text": "sentence", "label": "label", "id": "id"}, "sample": 6,
                   "drop_labels": ["neutral"], "label_group": "sentiment", "question": "importers.sst2", "licence": "CC-BY-SA-4.0", **kw})

def nli_slot(**kw):
    return Slot(**{"source": "native", "pack": "Multilingual", "family": "HuCommitmentBank", "repo": "NYTK/HuCommitmentBank", "revision": "def456",
                   "files": ["nli/train.json", "nli/val.json"], "question_id": "relation",
                   "fields": {"premise": "premise", "hypothesis": "hypothesis", "label": "label", "id": "id"}, "sample": 6,
                   "label_group": "nli", "source_label_ids": {"entailment": "entailment", "neutral": "neutral", "contradiction": "contradiction"},
                   "question": "importers.xnli", "state": "importers.xnli_state", "licence": "CC-BY-SA-4.0", **kw})

# --- schema -------------------------------------------------------------------

def test_missing_slot_needs_reason():
    with pytest.raises(ValidationError, match="reason"): Slot(source="missing", pack="ABCD next action", family="ABCD")
    assert Slot(source="missing", pack="ABCD next action", family="ABCD", reason="later").reason == "later"

@pytest.mark.parametrize("drop", ["repo", "revision", "files"])
def test_native_slot_needs_repo_revision_and_files(drop):
    data = sentiment_slot().model_dump()
    data[drop] = [] if drop == "files" else None
    with pytest.raises(ValidationError, match=drop): Slot(**data)

def test_unknown_slot_field_is_rejected():
    with pytest.raises(ValidationError): Slot(source="generated", pack="Arena Fresh", family="Arena Fresh", smaple=3)

def test_repo_slots_load():
    en, hu = datasets.load_slots("en"), datasets.load_slots("hu")
    assert list(en) == list(hu)
    assert hu["abcd"].source == "missing" and hu["abcd"].reason == "separate frozen assessment; Hungarian ABCD is a follow-up"
    assert {k for k, s in hu.items() if s.source == "native"} == {"sst2", "agnews", "xnli", "massive"}
    assert {k for k, s in hu.items() if s.source == "translated"} == {"jevbench", "typed-decisions", "banking77", "scifact"}
    assert {k for k, s in en.items() if s.source == "generated"} == {"fresh", "robustness", "episodes"}
    assert all(s.source == "native" for k, s in en.items() if k not in ("fresh", "robustness", "episodes"))

def test_expected_counts_en_match_suites():
    counts = datasets.expected_counts("en")
    assert counts == suites.EXPECTED and sum(counts.values()) == 7671

def test_expected_counts_hu_full_total():
    counts = datasets.expected_counts("hu")
    assert sum(counts.values()) == 6871
    assert counts == {"JevBench public": 231, "Typed decisions": 2000, "Classification": 1500, "Multilingual": 200,
                      "RAG relevance": 500, "Arena Fresh": 1440, "Robustness": 1000}

# --- sampling -----------------------------------------------------------------

def test_stratified_is_identical_to_importers():
    rng = random.Random(1)
    rows = [{"label": rng.choice([0, 1, 2, "x"])} for _ in range(300)]
    for count in (1, 7, 100, 299):
        assert packs.stratified(rows, count) == importers.stratified(rows, count)
    assert packs.stratified(rows, 50, key="label") == importers.stratified(rows, 50, "label")
    with pytest.raises(ValueError): packs.stratified(rows, 301)

# --- native build -------------------------------------------------------------

def test_native_build_sentiment(offline):
    cases = native.build("hu", "sst2", sentiment_slot())
    names = labels("hu", "sentiment")
    assert len(cases) == 6
    assert Counter(c.provenance["label_ids"][c.gold] for c in cases) == {"negative": 3, "positive": 3}
    assert all(c.provenance["source_label"] != "neutral" for c in cases)
    for c in cases:
        assert c.id.startswith("hu:sst2-") and c.cluster == c.id and c.language == "hu" and c.label_status == "public"
        assert (c.pack, c.family, c.question.id, c.question.kind) == ("Classification", "HuSST", "label", "choice")
        assert c.question.labels == list(names.values()) == ["negatív", "pozitív"]
        assert c.gold in c.question.labels
        assert c.provenance["label_ids"] == {"negatív": "negative", "pozitív": "positive"}
        assert c.question.text == "Milyen érzelmet fejez ki ez a filmkritika?"
        assert c.state.startswith("Mondat ")
        p = c.provenance
        assert (p["repo"], p["revision"], p["licence"], p["slot"]) == ("NYTK/HuSST", "abc123", "CC-BY-SA-4.0", "sst2")
        assert set(p["files"]) == {"sentiment.parquet"} and len(p["files"]["sentiment.parquet"]) == 64
    assert offline[0][0] == "NYTK/HuSST" and offline[0][2]["revision"] == "abc123" and offline[0][2]["repo_type"] == "dataset"

def test_native_build_ids_follow_source_ids_and_stratified_order(offline):
    cases = native.build("hu", "sst2", sentiment_slot(sample=4))
    import pyarrow.parquet as pq
    rows = [r for r in pq.read_table(FIXTURES / "sentiment.parquet").to_pylist() if r["label"] != "neutral"]
    expected = [rows[i]["id"] for i in packs.stratified(rows, 4)]
    assert [c.id for c in cases] == [f"hu:sst2-{i}" for i in expected]

def test_native_build_pooled_pairs_with_state_template(offline):
    cases = native.build("hu", "xnli", nli_slot())
    assert len(cases) == 6 and len({c.id for c in cases}) == 6
    assert {c.id.split("-")[0] for c in cases} == {"hu:xnli"}
    assert {c.provenance["source_split"] for c in cases} == {"train", "val"}
    c = cases[0]
    assert c.question.id == "relation" and c.question.labels == ["következik", "semleges", "ellentmond"]
    assert c.state.startswith("Előfeltevés: ") and "\nHipotézis: " in c.state
    assert Counter(c.provenance["label_ids"][c.gold] for c in cases) == {"entailment": 2, "neutral": 2, "contradiction": 2}

def test_native_build_rejects_unknown_raw_label(offline):
    slot = nli_slot(source_label_ids={"entailment": "entailment", "neutral": "neutral"})
    with pytest.raises(ValueError, match="contradiction"): native.build("hu", "xnli", slot)

def test_native_build_insufficient_rows(offline):
    with pytest.raises(ValueError, match="Insufficient"): native.build("hu", "sst2", sentiment_slot(sample=11))

def test_native_build_integer_labels_through_source_label_ids(offline, tmp_path, monkeypatch):
    import pyarrow as pa, pyarrow.parquet as pq
    rows = [{"id": str(i), "utt": f"kérés {i}", "intent": i % 2} for i in range(6)]
    pq.write_table(pa.Table.from_pylist(rows), tmp_path / "ints.parquet")
    monkeypatch.setattr(native, "hf_hub_download", lambda repo, filename, **kw: str(tmp_path / "ints.parquet"))
    slot = Slot(source="native", pack="Multilingual", family="MASSIVE", repo="AmazonScience/massive", revision="r", files=["hu-HU/test/0000.parquet"],
                fields={"text": "utt", "label": "intent", "id": "id"}, sample=4, label_group="massive_intents",
                source_label_ids={"0": "alarm_set", "1": "weather_query"}, question="importers.massive", question_id="intent")
    cases = native.build("hu", "massive", slot)
    hu = labels("hu", "massive_intents")
    assert len(cases[0].question.labels) == 60
    assert {c.gold for c in cases} == {hu["alarm_set"], hu["weather_query"]}
    assert {c.provenance["source_split"] for c in cases} == {"test"}

# --- packs --------------------------------------------------------------------

def test_save_writes_language_pack_and_manifest(offline, tmp_path):
    cases = native.build("hu", "sst2", sentiment_slot())
    packs.save("hu", "classification", cases, 6, licences={"sst2": "CC-BY-SA-4.0"}, revisions={"NYTK/HuSST": "abc123"})
    lines = (tmp_path / "hu" / "classification-cases.jsonl").read_text(encoding="utf-8").splitlines()
    assert [Case.model_validate_json(x) for x in lines] == cases
    manifest = json.loads((tmp_path / "hu" / "classification-manifest.json").read_text(encoding="utf-8"))
    assert manifest["language"] == "hu" and manifest["count"] == 6 and manifest["licences"] == {"sst2": "CC-BY-SA-4.0"}
    assert manifest["source_revisions"] == {"NYTK/HuSST": "abc123"} and manifest["case_ids"] == [c.id for c in cases]
    with pytest.raises(ValueError, match="expected 7"): packs.save("hu", "classification", cases, 7)
    with pytest.raises(ValueError, match="Duplicate"): packs.save("hu", "classification", cases + cases[:1], 7)

def test_prepare_language_builds_native_slots_into_pack_files(offline, tmp_path, monkeypatch):
    slots = {"sst2": sentiment_slot(), "xnli": nli_slot(), "fresh": Slot(source="generated", pack="Arena Fresh", family="Arena Fresh"),
             "banking77": Slot(source="translated", pack="Classification", family="BANKING77", sample=500),
             "abcd": Slot(source="missing", pack="ABCD next action", family="ABCD", reason="later")}
    monkeypatch.setattr(packs, "load_slots", lambda lang: slots)
    messages = []
    result = packs.prepare_language("hu", messages.append, only="native")
    assert result == {"classification": 6, "multilingual": 6}
    assert len((tmp_path / "hu" / "classification-cases.jsonl").read_text(encoding="utf-8").splitlines()) == 6
    assert any("sst2" in m for m in messages)
    # Rebuilding one slot keeps the other slots already in the pack file.
    slots["agnews"] = sentiment_slot(family="SIB-200")
    result = packs.prepare_language("hu", messages.append, only="native")
    assert result["classification"] == 12

def test_prepare_language_rejects_english():
    with pytest.raises(ValueError, match="importers"): packs.prepare_language("en")

# --- check --------------------------------------------------------------------

META = {"name": "N", "nativeName": "N", "status": "beta", "review": "r", "dir": "ltr"}

def write_locale(root, code, prompts, slots):
    d = root / code; d.mkdir(parents=True, exist_ok=True)
    (d / "locale.json").write_text(json.dumps({"code": code, **META}), encoding="utf-8")
    (d / "ui.json").write_text("{}", encoding="utf-8")
    (d / "prompts.yaml").write_text(yaml.safe_dump(prompts, allow_unicode=True), encoding="utf-8")
    if slots is not None: (d / "datasets.yaml").write_text(yaml.safe_dump({"slots": slots}, allow_unicode=True, sort_keys=False), encoding="utf-8")

PROMPTS = {"importers": {"sst2": "Q?"}, "labels": {"sentiment": {"negative": "negative", "positive": "positive"}}}
NATIVE = {"source": "native", "pack": "Classification", "family": "SST-2", "repo": "r/x", "revision": "1", "files": ["a.parquet"],
          "label_group": "sentiment", "question": "importers.sst2", "sample": 2}

def test_check_clean_datasets(tmp_path):
    write_locale(tmp_path, "en", PROMPTS, {"sst2": NATIVE})
    write_locale(tmp_path, "xx", PROMPTS, {"sst2": NATIVE})
    assert check.check("xx", tmp_path) == []

def test_check_unknown_label_group_and_prompt_key(tmp_path):
    write_locale(tmp_path, "en", PROMPTS, {"sst2": NATIVE})
    write_locale(tmp_path, "xx", PROMPTS, {"sst2": {**NATIVE, "label_group": "moods", "question": "importers.nope", "state": "importers"}})
    assert check.check("xx", tmp_path) == [
        check.Issue("error", "xx", "datasets.yaml", "sst2.label_group", "unknown label group 'moods'"),
        check.Issue("error", "xx", "datasets.yaml", "sst2.question", "unknown prompt key 'importers.nope'"),
        check.Issue("error", "xx", "datasets.yaml", "sst2.state", "unknown prompt key 'importers'"),
    ]

def test_check_schema_errors_and_slot_sets(tmp_path):
    write_locale(tmp_path, "en", PROMPTS, {"sst2": NATIVE, "abcd": {"source": "missing", "pack": "ABCD next action", "family": "ABCD", "reason": "r"}})
    write_locale(tmp_path, "xx", PROMPTS, {"sst2": {**NATIVE, "files": []}, "extra": {"source": "missing", "pack": "P", "family": "F", "reason": "r"}})
    issues = check.check("xx", tmp_path)
    assert [(i.level, i.key) for i in issues] == [("error", "sst2"), ("error", "extra"), ("error", "abcd")]
    assert "files" in issues[0].message
    assert issues[1].message == "slot not in en"
    assert issues[2].message == "slot missing (declare source: missing with a reason)"

def test_check_missing_datasets_yaml_is_warning_and_skipped_without_en(tmp_path):
    write_locale(tmp_path, "en", PROMPTS, None)
    write_locale(tmp_path, "xx", PROMPTS, None)
    assert check.check("xx", tmp_path) == []
    write_locale(tmp_path, "en", PROMPTS, {"sst2": NATIVE})
    assert check.check("xx", tmp_path) == [check.Issue("warning", "xx", "datasets.yaml", "", "datasets.yaml missing (no dataset slots in this language)")]

def test_check_invalid_yaml_structure(tmp_path):
    write_locale(tmp_path, "en", PROMPTS, {"sst2": NATIVE})
    write_locale(tmp_path, "xx", PROMPTS, None)
    (tmp_path / "xx" / "datasets.yaml").write_text("- a\n- b\n", encoding="utf-8")
    assert [(i.level, i.file) for i in check.check("xx", tmp_path)] == [("error", "datasets.yaml")]

def test_repo_datasets_have_no_check_errors():
    assert [i for i in check.check() if i.level == "error"] == []

def test_cli_prepare(monkeypatch, capsys):
    from arena.i18n.__main__ import main
    seen = {}
    def fake(lang, progress, only=None):
        seen.update(lang=lang, only=only); progress("sst2: 6 cases"); return {"classification": 6}
    monkeypatch.setattr(packs, "prepare_language", fake)
    assert main(["prepare", "--lang", "hu", "--only", "native"]) == 0
    assert seen == {"lang": "hu", "only": "native"}
    assert capsys.readouterr().out.splitlines() == ["sst2: 6 cases", "hu: 6 cases in 1 pack files"]
    monkeypatch.undo()
    assert main(["prepare", "--lang", "en"]) == 1
    assert capsys.readouterr().out.startswith("Error:")

def test_hu_sst2_uses_balanced_train_split():
    slot = datasets.load_slots("hu")["sst2"]
    assert slot.files == ["data/train.json"] and slot.drop_labels == ["neutral"] and (slot.sample, slot.seed) == (500, 5090)
