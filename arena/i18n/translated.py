"""Translated dataset slots: localized copies of prepared English packs, through a per-slot translation memory.

Translated: states, question texts, criteria descriptions, SciFact claims/titles/documents (split with the English
state template and rebuilt with the localized one), and native per-case choice label sets (typed decisions, JevBench).
Not translated: labels of slots with a prompts.yaml label group (BANKING77), questions that come from prompts.yaml,
binary labels ["no","yes"] and score labels "0".."4" (protocol ids).
"""
from __future__ import annotations
import json
import re
from collections import Counter
from typing import Callable, Iterable
from arena.config import DATASETS
from arena.contracts import Case, Question
from arena.i18n import engines, memory, prompts
from arena.i18n.datasets import Slot, load_slots
from arena.i18n.engines import Unavailable
from arena.i18n.memory import TranslationMemory
from arena.i18n.packs import PACK_FILES
from arena.i18n.prompts import labels as label_group, prompt

DEFAULT_ENGINE = "opus-mt"
TRIVIAL_RUBRICS = ("", "{}", "[]", "null")

class MissingTranslations(ValueError):
    def __init__(self, n: int, slot_id: str = "", rejected: int = 0):
        note = f"; {rejected} were rejected in review: fix them with review or tm import" if rejected else ""
        super().__init__(f"{slot_id}: {n} texts have no usable translation yet (run translate{note})")
        self.n, self.rejected = n, rejected

class EnglishMissing(Unavailable, FileNotFoundError):
    """The English pack this slot translates is not prepared."""

class LabelCollision(ValueError):
    """Two labels of one question translate to the same (case/underscore-insensitive) text."""

# --- English sources ------------------------------------------------------------

def english_cases(slot_id: str, slot: Slot) -> list[Case]:
    """The prepared English cases of the slot's pack (and family, when the pack mixes families)."""
    if slot.pack == "JevBench public":
        from arena.suites import jevbench
        cases = jevbench()
    else:
        if slot.pack not in PACK_FILES: raise ValueError(f"{slot_id}: no pack file for pack {slot.pack!r}")
        path = DATASETS / f"{PACK_FILES[slot.pack]}-cases.jsonl"
        cases = [Case.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
    cases = [c for c in cases if c.pack == slot.pack and c.language == "en"]
    if any(c.family == slot.family for c in cases): cases = [c for c in cases if c.family == slot.family]
    if not cases:
        raise EnglishMissing(f"prepare English datasets first: no English {slot.family} cases in {slot.pack} (use Prepare selected in Setup)")
    return cases

# --- translatable units ---------------------------------------------------------

def _template_regex(template: str) -> re.Pattern:
    parts = re.split(r"\{(\w+)\}", template)
    names = parts[1::2]
    pattern = ""
    for i, literal in enumerate(parts[0::2]):
        pattern += re.escape(literal)
        if i < len(names): pattern += f"(?P<{names[i]}>.*)" if i == len(names) - 1 else f"(?P<{names[i]}>.*?)"
    return re.compile(pattern, re.DOTALL)

def _state_fields(slot_id: str, slot: Slot, case: Case) -> dict[str, str]:
    match = _template_regex(prompts._node("en", slot.state)).fullmatch(case.state)  # the unformatted English template
    if not match: raise ValueError(f"{slot_id}: {case.id} state does not match the English template {slot.state}")
    return match.groupdict()

def _json_state(state: str):
    if not state.lstrip().startswith(("{", "[")): return None
    try: value = json.loads(state)
    except ValueError: return None
    return value if isinstance(value, (dict, list)) else None

# JSON states (JevBench): keys stay; each string value is a label id (-> its localized label), code-like (kept and
# recorded in provenance["untranslated_json_values"]) or natural language (translated through the TM).
_CODE_TOKEN = re.compile(r"\d|^[^\W\d_]*[_-][\w-]*$")

def _code_token(token: str) -> bool:
    letters = re.findall(r"[^\W\d_]", token)
    return (not letters or bool(_CODE_TOKEN.search(token)) or (len(letters) >= 2 and token.isupper())
            or (len(letters) == 1 and token.strip(".,;:!?()[]'\"").isupper()))

CHAT_ROLES = frozenset({"user", "assistant", "system"})  # protocol tokens in chat transcripts, not prose

def _title_case_run(tokens: list[str]) -> bool:
    """'Alex Moreno', 'Alex L.': every token with letters starts with an uppercase letter (names, titles)."""
    firsts = [m.group() for t in tokens if (m := re.search(r"[^\W\d_]", t))]
    return bool(firsts) and all(c.isupper() for c in firsts)

def json_value_kind(value: str, label_ids) -> str:
    """'label' (a choice label id), 'text' (translate) or 'keep' (code-like, a name, a chat role or otherwise not safely translatable)."""
    if value in label_ids: return "label"
    tokens = value.split()
    if not tokens or value.strip() in CHAT_ROLES or _title_case_run(tokens): return "keep"
    if len(tokens) == 1:
        word = tokens[0]
        return "text" if word.isalpha() and word.islower() else "keep"   # 'overdue' yes; 'ORD4711', 'escalate_to_manager', 'Alice' no
    # Natural language unless every token is code-like ('ORD 4711 A'); a sentence that mentions a number is still prose.
    return "keep" if all(_code_token(t) for t in tokens) else "text"

def _json_strings(value) -> Iterable[str]:
    if isinstance(value, dict): value = list(value.values())
    if isinstance(value, list):
        for item in value: yield from _json_strings(item)
    elif isinstance(value, str): yield value

def _json_map(value, convert):
    if isinstance(value, dict): return {k: _json_map(v, convert) for k, v in value.items()}
    if isinstance(value, list): return [_json_map(v, convert) for v in value]
    return convert(value) if isinstance(value, str) else value

def _choice_ids(case: Case) -> set[str]:
    return set(case.question.labels) if case.question.kind == "choice" else set()

def label_source(label: str) -> str:
    """Snake-case ids are translated as words: 'escalate_to_manager' -> 'escalate to manager'."""
    return label.replace("_", " ") if "_" in label and " " not in label else label

def translatable_label(label: str) -> bool:
    """Codes such as 'P1', 'A' or 'SEV2' stay as they are; words and snake-case ids are translated."""
    return len(re.findall(r"[^\W\d_]", label)) >= 2 and not re.search(r"\d", label) and not label.isupper()

EDGE_PUNCTUATION = ".,;:!?'\""

def localize_label(label: str, target: str) -> str:
    """Strip edge punctuation (.,;:!?'" and spaces); snake-case ids become lowercase_with_underscores, internal punctuation included."""
    target = target.strip().strip(EDGE_PUNCTUATION + " ").strip()
    if "_" in label and " " not in label: target = re.sub(r"[\s.,;:!?'\"_]+", "_", target.lower()).strip("_")
    return target

def _native_labels(slot: Slot, case: Case) -> bool:
    return case.question.kind == "choice" and slot.label_group is None

def _criteria_texts(case: Case) -> list[str]:
    criteria = case.question.criteria
    if criteria is None: return []
    if isinstance(criteria, dict): return list(criteria.values())
    return [] if case.question.kind == "choice" else list(criteria)  # a choice list holds labels

def _units(slot_id: str, slot: Slot, case: Case) -> list[str]:
    out = []
    if slot.state: out += list(_state_fields(slot_id, slot, case).values())
    elif (value := _json_state(case.state)) is not None:
        out += [v for v in _json_strings(value) if json_value_kind(v, _choice_ids(case)) == "text"]
    else: out.append(case.state)
    if not slot.question: out.append(case.question.text)
    out += _criteria_texts(case)
    if case.question.criteria is None and case.question.rubric not in TRIVIAL_RUBRICS: out.append(case.question.rubric)
    if _native_labels(slot, case): out += [label_source(label) for label in case.question.labels if translatable_label(label)]
    return out

def texts_for(slot_id: str, english_cases: list[Case], slot: Slot) -> list[str]:
    """Unique non-empty source texts the slot needs, in first-seen order."""
    seen: dict[str, None] = {}
    for case in english_cases:
        for text in _units(slot_id, slot, case):
            if text and text.strip(): seen.setdefault(text, None)
    return list(seen)

# --- translation ----------------------------------------------------------------

def translate(lang: str, slot_id: str, texts: list[str], engine_name: str, tm: TranslationMemory,
              progress: Callable[[str], None] | None = None, batch: int = 32) -> int:
    """Translate the texts missing from the memory; each batch is stored as it completes (resumable). Returns the count added."""
    say = progress or (lambda message: None)
    missing = tm.missing(texts)
    if not missing: return 0
    engine = engines.get(engine_name)
    if isinstance(engine, engines.ManualEngine):
        engine.pending_path = memory.pending_path(lang, slot_id)
        engine.translate(missing, "en", lang)  # raises ManualPending
    rejected = set(tm.rejected(missing))
    if rejected:  # the same engine would return the same text: rejected rows wait for an edit or tm import
        say(f"{slot_id}: {len(rejected)} rejected translations need review or tm import")
        missing = [t for t in missing if t not in rejected]
    added = empty = 0
    for i in range(0, len(missing), batch):
        chunk = missing[i:i + batch]
        out = engine.translate(chunk, "en", lang)
        if len(out) != len(chunk): raise engines.EngineError(f"{engine.name}: expected {len(chunk)} translations, got {len(out)}")
        pairs = [(s, t) for s, t in zip(chunk, out) if isinstance(t, str) and t.strip()]
        empty += len(chunk) - len(pairs)
        added += tm.put_many({"src": s, "tgt": t, "engine": engine.name, "model": engine.model, "revision": engine.revision} for s, t in pairs)
        say(f"{slot_id}: {min(i + batch, len(missing))}/{len(missing)} translated")
    if empty: say(f"{slot_id}: {engine.name} returned {empty} empty translations; they stay missing")
    return added

# --- build ----------------------------------------------------------------------

def _norm(label: str) -> str:
    return re.sub(r"[\s_]+", " ", label).strip().casefold()

def build(lang: str, slot_id: str, slot: Slot, english_cases: list[Case], tm: TranslationMemory) -> list[Case]:
    texts = texts_for(slot_id, english_cases, slot)
    absent = tm.missing(texts)
    if absent: raise MissingTranslations(len(absent), slot_id, rejected=len(tm.rejected(absent)))
    tm_sha = tm.sha256()
    group = label_group(lang, slot.label_group) if slot.label_group else None
    question_text = prompt(lang, slot.question) if slot.question else None
    out, collisions = [], []
    for case in english_cases:
        used: list[str] = []
        def tr(text: str) -> str:
            if not text or not text.strip(): return text
            target = tm.get(text)
            if not target or not target.strip(): raise MissingTranslations(1, slot_id)
            used.append(text)
            return target
        q = case.question
        if q.kind != "choice": label_map = {label: label for label in q.labels}
        elif group is not None:
            unknown = [label for label in q.labels if label not in group]
            if unknown: raise KeyError(f"{lang}:labels.{slot.label_group} has no {unknown}")
            label_map = {label: group[label] for label in q.labels}
        else: label_map = {label: localize_label(label, tr(label_source(label))) if translatable_label(label) else label for label in q.labels}
        values = list(label_map.values())
        dupes = [k for k, n in Counter(_norm(v) for v in values).items() if n > 1]
        if dupes or any(not v for v in values):
            collisions.append(f"{case.id}: {label_map}")
            continue
        if slot.state: state = prompt(lang, slot.state, **{k: tr(v) for k, v in _state_fields(slot_id, slot, case).items()})
        elif (value := _json_state(case.state)) is not None:
            kept: list[str] = []
            def convert(v: str) -> str:
                kind = json_value_kind(v, label_map if q.kind == "choice" else ())
                if kind == "label": return label_map[v]
                if kind == "text": return tr(v)
                if re.search(r"[^\W\d_]", v) and v not in kept: kept.append(v)
                return v
            state = json.dumps(_json_map(value, convert), ensure_ascii=False)
        else: state = tr(case.state)
        text = question_text if question_text is not None else tr(q.text)
        criteria = q.criteria
        if isinstance(criteria, dict):
            criteria = {(label_map.get(k, k) if q.kind == "choice" else k): tr(v) for k, v in criteria.items()}
        elif isinstance(criteria, list):
            criteria = [label_map.get(v, v) for v in criteria] if q.kind == "choice" else [tr(v) for v in criteria]
        if criteria is not None: rubric = json.dumps(criteria, ensure_ascii=False)
        elif q.rubric in TRIVIAL_RUBRICS: rubric = q.rubric
        else: rubric = tr(q.rubric)
        question = Question(id=q.id, text=text, kind=q.kind, labels=values, rubric=rubric, criteria=criteria)
        rows = [tm.row(t) for t in dict.fromkeys(used)]
        provenance = {k: v for k, v in case.provenance.items() if k != "native_question"}
        if "native_question" in case.provenance:
            native = {"type": q.kind, "instructions": text}
            if "criteria" in case.provenance["native_question"]: native["criteria"] = criteria
            provenance["native_question"] = native
        if (value := _json_state(case.state)) is not None and not slot.state: provenance["untranslated_json_values"] = kept
        if slot.needs_review: provenance["needs_review"] = True
        provenance |= {"slot": slot_id, "translated_from": case.id, "engine": sorted({r["engine"] for r in rows}), "tm_sha256": tm_sha,
                       "reviewed_fraction": round(sum(r["reviewed"] for r in rows) / len(rows), 4) if rows else 1.0}
        if q.kind == "choice": provenance["label_ids"] = {v: k for k, v in label_map.items()}
        remap = lambda label: label_map[label]
        out.append(case.model_copy(update={
            "id": f"{lang}:{case.id}", "cluster": f"{lang}:{case.cluster}", "language": lang, "state": state, "question": question,
            "gold": remap(case.gold), "acceptable": [remap(a) for a in case.acceptable],
            "reference_probs": {remap(k): v for k, v in case.reference_probs.items()} if case.reference_probs is not None else None,
            "provenance": provenance}))
    if collisions:
        raise LabelCollision(f"{slot_id}: translated labels collide or are empty in {len(collisions)} cases (fix them with review or tm import): "
                             + "; ".join(collisions))
    return [Case.model_validate(c.model_dump()) for c in out]  # re-validate labels and gold

def prepare_slot(lang: str, slot_id: str, slot: Slot, progress: Callable[[str], None] | None = None) -> list[Case]:
    english = english_cases(slot_id, slot)
    tm = TranslationMemory(lang, slot_id)
    translate(lang, slot_id, texts_for(slot_id, english, slot), slot.engine or DEFAULT_ENGINE, tm, progress)
    return build(lang, slot_id, slot, english, tm)
