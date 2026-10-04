"""Owned, executable-policy fixtures. References derive from rules, never candidates.

These are deliberately labeled formal cases; they are not a substitute for a
human-audited open-ended semantic benchmark. Split-specific vocabulary and
presentation varies across dev/calibration/test; policy templates remain shared.
"""
from __future__ import annotations
import random
from arena.contracts import Case, Question
from arena.i18n.prompts import labels, prompt

FAMILIES = ["Support routing", "Workflow permissions", "Evidence review", "Tool selection", "Document triage", "Relevance", "Abstention", "Consistency"]
LEVELS = ["0", "1", "2", "3", "4"]
FIXTURE_VERSION = "formal-v2"

def scenario(family: int, index: int, split: str = "test", counterfactual=False, lang: str = "en"):
    salt = {"dev": 117001, "calibration": 133001, "test": 159001}[split]
    rng = random.Random(salt + family * 1009 + index)
    a, b, c = (rng.choice([False, True]) for _ in range(3))
    if counterfactual: a = not a
    n = rng.randrange(1, 5)
    # Every string comes from locales/<lang>/prompts.yaml; the logic and RNG calls are shared by all languages,
    # so the proof fields and golds are identical across languages. Code-produced words are looked up by stable id.
    t = lambda key, **kw: prompt(lang, f"fresh.{key}", **kw)
    p = lambda key, **kw: t(f"family{family}.{key}", **kw)
    entity = f"{t(f'split_entity.{split}')}-{family+1}-{index+1:03}"
    yes = lambda x: t("yes") if x else t("no")
    # Each tuple defines evidence, question, choice options, gold, binary and ordinal targets.
    # Choice options and golds are stable English ids, localized through labels(lang, "fresh_choice") below.
    if family == 0:
        topic = "payment" if a else ("outage" if b else "onboarding")
        state = p("state", entity=entity, topic=p(f"topics.{topic}"), unavailable=yes(c), n=n)
        choice = (p("choice"), ["Billing", "Engineering", "Success"], {"payment":"Billing","outage":"Engineering","onboarding":"Success"}[topic])
        binary, ordinal = (p("binary"), c), (p("ordinal"), n)
    elif family == 1:
        result = "Proceed" if a and b else "Review" if a else "Stop"
        state = p("state", entity=entity, eligible=yes(a), approved=yes(b), n=n)
        choice = (p("choice"), ["Proceed","Review","Stop"], result)
        binary, ordinal = (p("binary"), not (a and b)), (p("ordinal"), n)
    elif family == 2:
        stated = "opened" if a else "closed"
        claim = stated if b else ("closed" if a else "opened")
        state = p("state", entity=entity, stated=p(f"status.{stated}"), claim=p(f"status.{claim}"), n=n)
        choice = (p("choice"), ["Supported","Contradicted","Insufficient evidence"], "Supported" if b else "Contradicted")
        binary, ordinal = (p("binary"), not b), (p("ordinal"), 4 if b else 0)
    elif family == 3:
        desired = "write" if a else "read"
        state = p("state", entity=entity, desired=p(f"access.{desired}"), approval=yes(b))
        choice = (p("choice"), ["Reader","Editor","Request approval"], "Reader" if not a else "Editor" if b else "Request approval")
        binary, ordinal = (p("binary"), a and not b), (p("ordinal"), 0 if a else 4)
    elif family == 4:
        state = p("state", entity=entity, confidential=yes(a), signed=yes(b), n=n)
        choice = (p("choice"), ["Secure review","Intake","Archive"], "Secure review" if a else "Intake" if not b else "Archive")
        binary, ordinal = (p("binary"), not b), (p("ordinal"), n)
    elif family == 5:
        product = "Atlas" if a else "Boreal"
        docproduct = product if b else ("Boreal" if a else "Atlas")
        state = p("state", entity=entity, product=p(f"products.{product}"), docproduct=p(f"products.{docproduct}"), n=n)
        choice = (p("choice"), ["Relevant","Not relevant"], "Relevant" if b else "Not relevant")
        binary, ordinal = (p("binary"), b), (p("ordinal"), 4 if b else 0)
    elif family == 6:
        rec1 = "active" if a else "inactive"
        rec2 = rec1 if b else ("inactive" if a else "active")
        state = p("state", entity=entity, rec1=p(f"status.{rec1}"), rec2=p(f"status.{rec2}"))
        # Stable id instead of rec1.title(): equal in English, and never title-cases a translated word.
        choice = (p("choice"), ["Active","Inactive","Unknown"], {"active": "Active", "inactive": "Inactive"}[rec1] if b else "Unknown")
        binary, ordinal = (p("binary"), not b), (p("ordinal"), 4 if b else 0)
    else:
        severity = 4 if a else 2 if b else 0
        state = p("state", entity=entity, data_loss=yes(a), degraded=yes(b), notified=yes(c))
        choice = (p("choice"), ["Critical","Warning","Healthy"], "Critical" if a else "Warning" if b else "Healthy")
        binary, ordinal = (p("binary"), a), (p("ordinal"), severity)
    # Different presentation families per split; all essential semantics explicit.
    pres = lambda key: t(f"presentation.{key}")
    if split == "dev": state = pres("dev_prefix") + state.replace(pres("policy_word"), pres("dev_policy_word"))
    if split == "calibration": state = pres("calibration_prefix") + state.replace(pres("policy_word"), pres("calibration_policy_word"))
    localized = lang != "en"
    cluster = f"fresh-v2-{split}-{family:02}-{index:03}"
    if localized: cluster = f"{lang}:{cluster}"
    names = labels(lang, "fresh_choice")
    choice_labels = [names[x] for x in choice[1]]
    # Binary golds stay the protocol ids no/yes and score golds 0..4 in every language; only choices are localized.
    definitions = [("choice",choice[0],choice_labels,names[choice[2]]),("noul",binary[0],["no","yes"],"yes" if binary[1] else "no"),("score",ordinal[0],LEVELS,str(ordinal[1]))]
    rubric = t("rubric")
    def provenance(kind):
        out = {"source":"owned","generator":FIXTURE_VERSION,"family":family,"index":index,"proof":{"a":a,"b":b,"c":c,"n":n},"semantic_audit":"not claimed"}
        if localized and kind == "choice": out["label_ids"] = dict(zip(choice_labels, choice[1]))
        return out
    # pack and family (FAMILIES display names) stay English in every language: they are identifiers the UI translates.
    return [Case(id=f"{cluster}-{kind}", cluster=cluster, pack="Arena Fresh", family=FAMILIES[family], state=state,
        question=Question(id=kind,text=text,kind=kind,labels=labels_,rubric=rubric), gold=gold,
        evidence=state, split=split, label_status="formal", provenance=provenance(kind), language=lang)
        for kind,text,labels_,gold in definitions]

def fresh(split="test", lang: str = "en") -> list[Case]:
    count = 60 if split == "test" else 15
    return [c for f in range(8) for i in range(count) for c in scenario(f,i,split,lang=lang)]

def robustness(lang: str = "en") -> list[Case]:
    anchors = [scenario(f,i,lang=lang)[0] for i in range(25) for f in range(8)]
    out=[]
    for anchor in anchors:
        f,i = anchor.provenance["family"],anchor.provenance["index"]
        for variant in ("reversed_options","paraphrase","distractor","injection","counterfactual"):
            case = anchor.model_copy(deep=True)
            if variant == "reversed_options": case.question.labels.reverse()
            elif variant == "paraphrase":
                case.question.text = prompt(lang, "robustness.paraphrase_prefix") + case.question.text
                # Provenance note is metadata, not test text: it stays English in every language.
                case.provenance["paraphrase_status"] = "mechanical rephrasing; human review pending"
            elif variant == "distractor": case.state += prompt(lang, "robustness.distractor")
            elif variant == "injection": case.state += prompt(lang, "robustness.injection")
            else:
                # Change a causal fact. Find the first altered input with a different gold (same language).
                for delta in range(1,200):
                    alternative=scenario(f,i+delta,lang=lang)[0]
                    if alternative.gold != anchor.gold:
                        case.state,case.gold,case.evidence=alternative.state,alternative.gold,alternative.evidence
                        case.provenance["counterfactual_source_index"]=i+delta
                        break
            case.id += "-"+variant
            case.pack="Robustness"
            case.variant=variant
            case.provenance["anchor_id"]=anchor.id
            out.append(case)
    return out

def smoke(lang: str = "en"):
    return [c for i in range(2) for f in range(6) for c in scenario(f,i,lang=lang)]
