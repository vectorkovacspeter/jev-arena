"""Translation engines, translation memory and translated packs. Offline: the `fake` engine and mocked HTTP only."""
import json
import httpx
import pytest
from arena.contracts import Case, Question
from arena.i18n import engines, memory, packs, translated
from arena.i18n.__main__ import main
from arena.i18n.datasets import Slot
from arena.i18n.prompts import labels, prompt

@pytest.fixture
def tm_root(monkeypatch, tmp_path):
    monkeypatch.setattr(memory, "TRANSLATIONS", tmp_path / "translations")
    return tmp_path / "translations"

def fake_rows(texts, tgt="hu"):
    return [{"src": t, "tgt": f"[{tgt}] {t}", "engine": "fake", "model": "fake", "revision": "0"} for t in texts]

# --- English fixture pack -----------------------------------------------------

TYPED = Slot(source="translated", pack="Typed decisions", family="Typed decisions", sample=4, engine="fake")
BANKING = Slot(source="translated", pack="Classification", family="BANKING77", sample=1, label_group="banking77", question="importers.banking77", engine="fake")
SCIFACT = Slot(source="translated", pack="RAG relevance", family="SciFact", sample=1, question="importers.scifact", state="importers.scifact_state", engine="fake")

def typed_cases():
    choice_criteria = {"escalate_to_manager": "The manager must decide.", "close_ticket": "Nothing left to do.", "Review": "Needs a second look."}
    probs = {"escalate_to_manager": 0.7, "close_ticket": 0.1, "Review": 0.2}
    choice = Case(id="typed-r1-q1", cluster="typed-r1", pack="Typed decisions", family="refunds", state="A customer asks for a refund.\nThe order is late.",
                  question=Question(id="q1", kind="choice", text="What should happen next?", labels=list(probs), criteria=choice_criteria,
                                    rubric=json.dumps(choice_criteria)),
                  gold="escalate_to_manager", acceptable=["Review"], reference_probs=probs, label_status="teacher",
                  provenance={"source": "x", "native_question": {"type": "choice", "instructions": "What should happen next?", "criteria": choice_criteria}})
    noul_criteria = {"true": "It is urgent.", "false": "It can wait."}
    noul = Case(id="typed-r1-q2", cluster="typed-r1", pack="Typed decisions", family="refunds", state="A customer asks for a refund.\nThe order is late.",
                question=Question(id="q2", kind="noul", text="Is it urgent?", labels=["no", "yes"], criteria=noul_criteria, rubric=json.dumps(noul_criteria)),
                gold="yes", reference_probs={"no": 0.2, "yes": 0.8}, label_status="teacher")
    score_criteria = ["No impact.", "Low impact.", "Some impact.", "High impact.", "Severe impact."]
    score = Case(id="typed-r1-q3", cluster="typed-r1", pack="Typed decisions", family="refunds", state="A customer asks for a refund.\nThe order is late.",
                 question=Question(id="q3", kind="score", text="How severe is it?", labels=["0", "1", "2", "3", "4"], criteria=score_criteria,
                                   rubric=json.dumps(score_criteria)),
                 gold="3", reference_probs={"0": 0.0, "1": 0.1, "2": 0.2, "3": 0.6, "4": 0.1}, label_status="teacher")
    plain = Case(id="typed-r2-q1", cluster="typed-r2", pack="Typed decisions", family="access", state="Grant access?",
                 question=Question(id="q1", kind="choice", text="Pick one.", labels=["Review", "close_ticket"]), gold="Review", label_status="teacher")
    return [choice, noul, score, plain]

def banking_case():
    names = list(labels("en", "banking77"))
    return Case(id="classification-banking77-7", cluster="classification-banking77-7", pack="Classification", family="BANKING77",
                state="My card still has not arrived.", question=Question(id="label", kind="choice", text="Which banking intent best describes this customer request?",
                labels=names), gold="card_arrival", label_status="public", provenance={"source": "hf"})

def scifact_case():
    return Case(id="scifact-1-99", cluster="scifact-1", pack="RAG relevance", family="SciFact",
                state="Claim: Aspirin lowers fever.\nDocument title: Fever study\nDocument: We studied aspirin.\nIt lowered fever.",
                question=Question(id="relevance", kind="noul", text="Does this document provide relevant evidence for verifying or refuting the claim?", labels=["no", "yes"]),
                gold="yes", label_status="public", provenance={"query_id": "1"})

# --- translation memory -------------------------------------------------------

def test_tm_round_trip_skips_duplicates_and_resumes(tm_root):
    tm = memory.TranslationMemory("hu", "typed-decisions")
    assert tm.missing(["a", "b", "a"]) == ["a", "b"]
    assert tm.put_many(fake_rows(["a"])) == 1
    assert tm.put_many(fake_rows(["a", "b"])) == 1          # "a" is not stored twice
    assert tm.get("a") == "[hu] a" and tm.get("c") is None
    again = memory.TranslationMemory("hu", "typed-decisions")  # resume from disk
    assert again.missing(["a", "b", "c"]) == ["c"] and again.get("b") == "[hu] b"
    lines = (tm_root / "hu" / "typed-decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert set(row) == {"src_sha256", "src", "tgt", "engine", "model", "revision", "at", "reviewed"} and row["reviewed"] is False
    assert row["src_sha256"] == memory.src_sha("a") and len(again.sha256()) == 64

def test_translate_only_missing_texts(tm_root, monkeypatch):
    seen = []
    class Counting(engines.FakeEngine):
        def translate(self, texts, src, tgt):
            seen.append(list(texts)); return super().translate(texts, src, tgt)
    monkeypatch.setitem(engines.ENGINES, "fake", Counting)
    tm = memory.TranslationMemory("hu", "s")
    assert translated.translate("hu", "s", ["x", "y", "x"], "fake", tm) == 2
    assert translated.translate("hu", "s", ["x", "y", "z"], "fake", tm) == 1
    assert seen == [["x", "y"], ["z"]]
    assert tm.get("z") == "[hu] z" and tm.row("z")["engine"] == "fake"

def test_tm_export_import_keeps_reviewed(tm_root, tmp_path):
    tm = memory.TranslationMemory("hu", "s")
    tm.put_many(fake_rows(["a", "b"]))
    tm.update("a", reviewed=True)
    out = tmp_path / "export.jsonl"
    tm.export(out)
    other = memory.TranslationMemory("hu", "other")
    assert other.import_(out) == 2
    assert other.row("a")["reviewed"] is True and other.row("b")["reviewed"] is False and other.get("b") == "[hu] b"

def test_manual_engine_writes_pending_then_imports(tm_root, tmp_path):
    tm = memory.TranslationMemory("hu", "banking77")
    with pytest.raises(engines.ManualPending) as info:
        translated.translate("hu", "banking77", ["Hello", "World"], "manual", tm)
    path = info.value.path
    assert path == tm_root / "hu" / "banking77.pending.jsonl"
    pending = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert pending == [{"src_sha256": memory.src_sha("Hello"), "src": "Hello"}, {"src_sha256": memory.src_sha("World"), "src": "World"}]
    done = tmp_path / "done.jsonl"
    done.write_text("\n".join(json.dumps({"src_sha256": r["src_sha256"], "tgt": "Szia" if r["src"] == "Hello" else "Világ"}) for r in pending), encoding="utf-8")
    assert main(["tm", "import", "--lang", "hu", "--slot", "banking77", str(done)]) == 0
    tm = memory.TranslationMemory("hu", "banking77")
    assert tm.get("Hello") == "Szia" and tm.get("World") == "Világ" and tm.row("Hello")["engine"] == "manual"
    assert tm.missing(["Hello", "World"]) == []

def test_import_rejects_unknown_source(tm_root, tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"src_sha256": "0" * 64, "tgt": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown source"): memory.TranslationMemory("hu", "s").import_(bad)

# --- engines ------------------------------------------------------------------

def test_fake_engine_and_registry():
    assert engines.get("fake").translate(["a"], "en", "hu") == ["[hu] a"]
    assert "fake" not in engines.PUBLIC and set(engines.PUBLIC) == {"manual", "opus-mt", "deepl", "google"}
    with pytest.raises(ValueError, match="opus-mt"): engines.get("nope")

def test_opus_mt_missing_dependencies_name_the_extra(monkeypatch):
    monkeypatch.setattr(engines, "find_spec", lambda name: None)
    with pytest.raises(engines.EngineUnavailable, match=r"uv sync --frozen --extra dev --extra i18n"): engines.get("opus-mt")

def test_opus_mt_revision_is_pinned():
    assert len(engines.OPUS_MT_REVISIONS["Helsinki-NLP/opus-mt-en-hu"]) == 40

def test_split_long_on_sentence_boundaries():
    count = lambda s: len(s.split())
    short = "One two three."
    assert engines.split_long(short, count, limit=5) == [short]
    text = "One two three. Four five six. Seven eight nine ten eleven twelve."
    parts = engines.split_long(text, count, limit=6)
    assert parts == ["One two three. Four five six.", "Seven eight nine ten eleven twelve."]
    assert all(count(p) <= 6 for p in parts)
    words = " ".join(f"w{i}" for i in range(13))
    assert all(count(p) <= 5 for p in engines.split_long(words, count, limit=5)) and " ".join(engines.split_long(words, count, limit=5)) == words

@pytest.mark.parametrize("name,var", [("deepl", "DEEPL_API_KEY"), ("google", "GOOGLE_TRANSLATE_API_KEY")])
def test_api_engines_need_keys(monkeypatch, name, var):
    monkeypatch.delenv(var, raising=False)
    with pytest.raises(engines.EngineUnavailable, match=var): engines.get(name)

def test_deepl_engine_over_mock_transport(monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "secret-key:fx")
    seen = []
    def handler(request):
        seen.append(request)
        body = json.loads(request.content)
        return httpx.Response(200, json={"translations": [{"text": "HU " + t} for t in body["text"]]})
    engine = engines.DeepLEngine(client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert engine.translate(["a", "b"], "en", "hu") == ["HU a", "HU b"]
    assert str(seen[0].url) == "https://api-free.deepl.com/v2/translate"
    assert seen[0].headers["Authorization"] == "DeepL-Auth-Key secret-key:fx"
    assert json.loads(seen[0].content)["target_lang"] == "HU"
    assert "secret" not in repr(engine)

def test_google_engine_errors_never_show_the_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "goog-secret")
    def handler(request):
        assert request.headers["X-Goog-Api-Key"] == "goog-secret" and "goog-secret" not in str(request.url)
        body = json.loads(request.content)
        if body["q"] == ["boom"]: return httpx.Response(403, json={"error": {"message": "denied"}})
        return httpx.Response(200, json={"data": {"translations": [{"translatedText": "HU " + t} for t in body["q"]]}})
    engine = engines.GoogleEngine(client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert engine.translate(["a"], "en", "hu") == ["HU a"]
    with pytest.raises(engines.EngineError) as info: engine.translate(["boom"], "en", "hu")
    assert "403" in str(info.value) and "goog-secret" not in str(info.value)

# --- texts and builds ---------------------------------------------------------

def test_texts_for_lists_unique_sources_without_label_groups():
    texts = translated.texts_for("typed-decisions", typed_cases(), TYPED)
    assert len(texts) == len(set(texts))
    for t in ["A customer asks for a refund.\nThe order is late.", "What should happen next?", "The manager must decide.", "It is urgent.",
              "Severe impact.", "escalate to manager", "close ticket", "Review", "Pick one."]:
        assert t in texts
    assert "no" not in texts and "3" not in texts and "true" not in texts
    bank = translated.texts_for("banking77", [banking_case()], BANKING)
    assert bank == ["My card still has not arrived."]          # labels and question come from prompts.yaml
    assert translated.texts_for("scifact", [scifact_case()], SCIFACT) == ["Aspirin lowers fever.", "Fever study", "We studied aspirin.\nIt lowered fever."]

def test_build_raises_on_missing_translations(tm_root):
    tm = memory.TranslationMemory("hu", "typed-decisions")
    texts = translated.texts_for("typed-decisions", typed_cases(), TYPED)
    tm.put_many(fake_rows(texts[:-2]))
    with pytest.raises(translated.MissingTranslations) as info: translated.build("hu", "typed-decisions", TYPED, typed_cases(), tm)
    assert info.value.n == 2

def test_translated_build_remaps_labels_gold_criteria_and_probs(tm_root):
    english = typed_cases()
    tm = memory.TranslationMemory("hu", "typed-decisions")
    translated.translate("hu", "typed-decisions", translated.texts_for("typed-decisions", english, TYPED), "fake", tm)
    tm.update("Review", reviewed=True)
    choice, noul, score, plain = translated.build("hu", "typed-decisions", TYPED, english, tm)
    assert choice.id == "hu:typed-r1-q1" and choice.cluster == "hu:typed-r1" and choice.language == "hu" and choice.family == "refunds"
    assert choice.state == "[hu] A customer asks for a refund.\nThe order is late."
    assert choice.question.text == "[hu] What should happen next?"
    assert choice.question.labels == ["[hu]_escalate_to_manager", "[hu]_close_ticket", "[hu] Review"]
    assert choice.gold == "[hu]_escalate_to_manager" and choice.acceptable == ["[hu] Review"]
    assert choice.reference_probs == {"[hu]_escalate_to_manager": 0.7, "[hu]_close_ticket": 0.1, "[hu] Review": 0.2}
    assert choice.question.criteria == {"[hu]_escalate_to_manager": "[hu] The manager must decide.", "[hu]_close_ticket": "[hu] Nothing left to do.",
                                        "[hu] Review": "[hu] Needs a second look."}
    assert json.loads(choice.question.rubric) == choice.question.criteria
    assert choice.provenance["label_ids"] == {"[hu]_escalate_to_manager": "escalate_to_manager", "[hu]_close_ticket": "close_ticket", "[hu] Review": "Review"}
    assert choice.provenance["translated_from"] == "typed-r1-q1" and choice.provenance["engine"] == ["fake"]
    assert choice.provenance["tm_sha256"] == tm.sha256() and choice.provenance["slot"] == "typed-decisions"
    assert 0 < choice.provenance["reviewed_fraction"] < 1
    assert choice.provenance["native_question"] == {"type": "choice", "instructions": "[hu] What should happen next?", "criteria": choice.question.criteria}
    assert noul.question.labels == ["no", "yes"] and noul.gold == "yes" and noul.reference_probs == {"no": 0.2, "yes": 0.8}
    assert noul.question.criteria == {"true": "[hu] It is urgent.", "false": "[hu] It can wait."}
    assert score.question.labels == ["0", "1", "2", "3", "4"] and score.gold == "3" and score.question.criteria[4] == "[hu] Severe impact."
    assert "label_ids" not in noul.provenance and "label_ids" not in score.provenance
    assert plain.question.labels == ["[hu] Review", "[hu]_close_ticket"] and plain.question.criteria is None and plain.question.rubric == ""

def test_label_codes_are_not_translated(tm_root):
    case = Case(id="typed-r3-q1", cluster="typed-r3", pack="Typed decisions", family="triage", state="Pick a priority.",
                question=Question(id="q1", kind="choice", text="Which priority?", labels=["P1", "P2", "SEV", "A"]), gold="P2", label_status="teacher")
    assert translated.texts_for("typed-decisions", [case], TYPED) == ["Pick a priority.", "Which priority?"]
    tm = memory.TranslationMemory("hu", "typed-decisions")
    translated.translate("hu", "typed-decisions", ["Pick a priority.", "Which priority?"], "fake", tm)
    (built,) = translated.build("hu", "typed-decisions", TYPED, [case], tm)
    assert built.question.labels == ["P1", "P2", "SEV", "A"] and built.gold == "P2" and built.provenance["label_ids"] == {"P1": "P1", "P2": "P2", "SEV": "SEV", "A": "A"}

def test_translated_labels_must_stay_unique(tm_root):
    english = typed_cases()
    tm = memory.TranslationMemory("hu", "typed-decisions")
    texts = translated.texts_for("typed-decisions", english, TYPED)
    tm.put_many([{**r, "tgt": "Ugyanaz" if r["src"] in ("Review", "close ticket") else r["tgt"]} for r in fake_rows(texts)])
    with pytest.raises(translated.LabelCollision, match="typed-r1-q1"): translated.build("hu", "typed-decisions", TYPED, english, tm)

def test_banking_build_uses_label_group(tm_root):
    tm = memory.TranslationMemory("hu", "banking77")
    tm.put_many(fake_rows(["My card still has not arrived."]))
    (case,) = translated.build("hu", "banking77", BANKING, [banking_case()], tm)
    group = labels("hu", "banking77")
    assert case.gold == group["card_arrival"] and case.question.labels == [group[x] for x in labels("en", "banking77")]
    assert case.question.text == prompt("hu", "importers.banking77") and case.provenance["label_ids"][case.gold] == "card_arrival"

def test_scifact_build_rebuilds_state_template(tm_root):
    tm = memory.TranslationMemory("hu", "scifact")
    translated.translate("hu", "scifact", translated.texts_for("scifact", [scifact_case()], SCIFACT), "fake", tm)
    (case,) = translated.build("hu", "scifact", SCIFACT, [scifact_case()], tm)
    assert case.state == prompt("hu", "importers.scifact_state", claim="[hu] Aspirin lowers fever.", title="[hu] Fever study",
                                text="[hu] We studied aspirin.\nIt lowered fever.")
    assert case.question.labels == ["no", "yes"] and case.gold == "yes" and case.question.text == prompt("hu", "importers.scifact")

def test_banking77_labels_complete_and_unique():
    en, hu = labels("en", "banking77"), labels("hu", "banking77")
    assert len(en) == 77 and list(en) == list(hu) and all(k == v for k, v in en.items())
    assert "Refund_not_showing_up" in en and "reverted_card_payment?" in en
    assert len(set(hu.values())) == 77
    assert all(v == v.lower() and " " not in v for v in hu.values())

# --- prepare and CLI ----------------------------------------------------------

def test_prepare_translated_slot_and_missing_english(tm_root, monkeypatch, tmp_path):
    monkeypatch.setattr(packs, "DATASETS", tmp_path / "datasets")
    monkeypatch.setattr(translated, "DATASETS", tmp_path / "datasets")
    slots = {"typed-decisions": TYPED, "banking77": BANKING}
    monkeypatch.setattr(packs, "load_slots", lambda lang: slots)
    (tmp_path / "datasets").mkdir()
    (tmp_path / "datasets" / "typed-cases.jsonl").write_text("\n".join(c.model_dump_json() for c in typed_cases()) + "\n", encoding="utf-8")
    messages = []
    result = packs.prepare_language("hu", messages.append, only="translated")
    assert result == {"typed": 4}
    assert any("banking77" in m and "prepare English datasets first" in m for m in messages)
    cases = packs.read_pack("hu", "typed")
    assert [c.id for c in cases] == ["hu:typed-r1-q1", "hu:typed-r1-q2", "hu:typed-r1-q3", "hu:typed-r2-q1"]
    assert all(c.provenance["slot"] == "typed-decisions" for c in cases)

def test_cli_translate_dry_run_counts_characters(tm_root, monkeypatch, capsys):
    monkeypatch.setattr(translated, "english_cases", lambda slot_id, slot: [scifact_case()])
    monkeypatch.setattr(translated, "load_slots", lambda lang: {"scifact": SCIFACT})
    assert main(["translate", "--lang", "hu", "--slot", "scifact", "--dry-run"]) == 0
    out = capsys.readouterr().out
    chars = len("Aspirin lowers fever.") + len("Fever study") + len("We studied aspirin.\nIt lowered fever.")
    assert "3 unique texts" in out and "3 to translate" in out and f"{chars} characters" in out and "500,000" in out
    assert not (tm_root / "hu" / "scifact.jsonl").exists()
    assert main(["translate", "--lang", "hu", "--slot", "scifact", "--engine", "fake"]) == 0
    assert "3 new translations" in capsys.readouterr().out
    assert main(["translate", "--lang", "hu", "--slot", "scifact", "--dry-run"]) == 0
    assert "0 to translate, 0 characters" in capsys.readouterr().out

def test_cli_translate_missing_english_is_an_error(tm_root, monkeypatch, capsys):
    def missing(slot_id, slot): raise translated.EnglishMissing(f"{slot_id}: prepare English datasets first")
    monkeypatch.setattr(translated, "english_cases", missing)
    assert main(["translate", "--lang", "hu", "--slot", "scifact", "--dry-run"]) == 1
    assert "prepare English datasets first" in capsys.readouterr().out

def test_cli_review_records_approvals_and_edits(tm_root, monkeypatch, capsys):
    tm = memory.TranslationMemory("hu", "s")
    tm.put_many(fake_rows(["a", "b", "c"]))
    answers = iter(["y", "x", "e", "Javított", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert main(["review", "--lang", "hu", "--slot", "s", "--sample", "3", "--seed", "1"]) == 0
    out = capsys.readouterr().out
    tm = memory.TranslationMemory("hu", "s")
    reviewed = [r for r in tm.rows() if r["reviewed"]]
    assert len(reviewed) == 2 and any(r["tgt"] == "Javított" for r in reviewed)
    assert "Reviewed 2" in out

def test_cli_tm_export(tm_root, tmp_path, capsys):
    memory.TranslationMemory("hu", "s").put_many(fake_rows(["a"]))
    out = tmp_path / "x.jsonl"
    assert main(["tm", "export", "--lang", "hu", "--slot", "s", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8").splitlines()[0])["tgt"] == "[hu] a"
