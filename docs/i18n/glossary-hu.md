# Hungarian glossary

Style rules:

- Use the informal second person singular (`te`): "Válassz", "Indítsd el", "Kattints".
- Nouns stay singular after numerals ("3 futtatás"). The catalogs still carry both `_one` and `_other` forms.
- Avoid number-dependent suffixes and articles ("{{n}} tervezett közül", not "-ból/-ből"; "ugyanazon {{n}} ...", not "a(z)").
- Keep acronyms and metric names: F1, Brier, MAE, P95, nDCG@10, MRR. Model and product names are not translated.
- SI symbols stay: ms, s. "pp" (percentage points) becomes "sz.p." (`common.pp`).
- "seed" stays "seed".
- Status: beta, needs native review.

## Core terms

| English | Hungarian |
|---|---|
| run (noun) | futtatás |
| test | teszt |
| case / question | eset / kérdés |
| model / entrant | modell / résztvevő |
| accuracy | pontosság |
| shared questions | közös kérdések |
| response time / latency | válaszidő / késleltetés |
| setup | beállítás |
| prepare | előkészítés |
| results | eredmények |
| workflow replay | munkafolyamat-visszajátszás |
| evidence | bizonyíték |
| report | jelentés |
| judge (audit) | bíráló |
| label | címke |
| pack / suite | csomag / tesztcsomag |
| support conversation | ügyfélszolgálati beszélgetés |
| percentage points (pp) | százalékpont (sz.p.) |
| benchmark | benchmark |
| checkpoint | ellenőrzőpont |

## Operations, results and setup

| English | Hungarian |
|---|---|
| smoke / demo / full (preset) | Gyors / Demó / Teljes |
| entrant comparison | résztvevők összehasonlítása |
| answer key | válaszkulcs |
| spot-check | szúrópróba |
| case manifest | esetlista |
| hosted / local | hosztolt / helyi |
| control (diagnostic model) | kontroll |
| typical response time | jellemző válaszidő |
| median | medián |
| log scale | logaritmikus skála |
| preflight / warming / unloading | előzetes ellenőrzés / bemelegítés / eltávolítás |
| queued / interrupted / partial | sorban áll / félbeszakadt / részleges |
| judging incomplete | bírálat hiányos |
| ready (status) / ready (model badge) | készen áll / kész |
| quality & confidence | minőség és megbízhatóság |
| triage | előszűrés |
| abstention | tartózkodás |
| support routing | ügyfélszolgálati irányítás |
| output contract | kimeneti szerződés |
| worker image | worker-lemezkép |
| experiment | kísérlet |

## Queues, topics, directions and statuses

| English | Hungarian |
|---|---|
| Billing / Engineering / Success / Review (queues) | Számlázás / Műszaki / Ügyfélsiker / Felülvizsgálat |
| prediction status: ok / invalid / timeout / transport error / unsupported / cancelled | rendben / érvénytelen / időtúllépés / átviteli hiba / nem támogatott / megszakítva |

Topics (`operations.topics.*`) and directions (`operations.directions.*`) are translated for display only; see `locales/hu/ui.json` for the exact wording.

## Explore, ABCD and Guide

| English | Hungarian |
|---|---|
| AI teacher / teacher labels | MI-tanár / MI-tanár címkék |
| question type | kérdéstípus |
| coverage / valid coverage | lefedettség / érvényes lefedettség |
| outcome | kimenet, kimenetel |
| retrieved policy | visszakeresett szabályzat |
| full handbook | teljes kézikönyv |
| confidence / confidence reliability | magabiztosság / a magabiztosság megbízhatósága |
| overconfident / underconfident | túl magabiztos / túl óvatos |
| What builders should take away | Tanulságok fejlesztőknek |
| Different jobs, different strengths | Más feladat, más erősség |
| Terms in plain English | Fogalmak közérthetően |
| Scope, audit and cost | Hatókör, ellenőrzés és költség |
| Answer accuracy, same questions | Válaszpontosság, ugyanazok a kérdések |
| Correct + usable output | Helyes + használható kimenet |
| strict accuracy | szigorú pontosság |
| matched | egyeztetett |
| perturbations | perturbációk |
| changed-input checks | módosított bemenetek ellenőrzése |
| precision used | használt numerikus pontosság |
| built from | erre épül |
| reference agreement | egyezés a referenciával |
| public answer key(s) | nyilvános válaszkulcs(ok) |
| AI-generated reference answers | MI által generált referenciaválaszok |
| public relevance labels | nyilvános relevanciacímkék |
| answers calculated from explicit rules | kifejezett szabályokból számított válaszok |
| test group | tesztcsoport |
| document relevance | dokumentumrelevancia |
| Arena policy tests | Arena szabályzati tesztek |
| policy template | szabályzatsablon |
| human validation | emberi validálás |
| ranking score | rangsorolási pontszám |

## Test data (locales/hu/prompts.yaml)

| English | Hungarian |
|---|---|
| slot (dataset slot) | tétel |
| Billing / Engineering / Success (fresh queues) | Számlázás / Műszaki / Ügyfélsiker |
| Proceed / Review / Stop | Folytatás / Felülvizsgálat / Leállítás |
| Supported / Contradicted / Insufficient evidence | Alátámasztott / Ellentmondó / Nincs elég bizonyíték |
| Reader / Editor | Olvasó / Szerkesztő |
| Request approval / Secure review | Jóváhagyás kérése / Biztonsági felülvizsgálat |
| Intake / Archive | Iktatás / Archívum |
| Relevant / Not relevant | Releváns / Nem releváns |
| Active / Inactive / Unknown | Aktív / Inaktív / Ismeretlen |
| Critical / Warning / Healthy | Kritikus / Figyelmeztetés / Rendben |
| yes / no (fresh state values) | igen / nem |
| north / east / south / west | észak / kelet / dél / nyugat |
| ticket | hibajegy |
| ticket topics: payment / service outage / onboarding (episodes) | fizetés / szolgáltatáskiesés / bevezetés |
| ticket topic: outage (Fresh `family1`) | kiesés — deliberately shorter than the episodes' "szolgáltatáskiesés"; each policy text names its own topic value, so keep the two apart |
| restricted account | korlátozott fiók |
| sentiment: negative / positive | negatív / pozitív |
| NLI: entailment / neutral / contradiction | következik / semleges / ellentmond |
| policy (in test text) | szabályzat |
| robustness distractor ("Unrelated warehouse memo: …") | Nem kapcsolódó raktári feljegyzés: … |
| robustness injection ("Quoted untrusted attachment (not a policy): …") | Idézett, nem megbízható melléklet (nem szabályzat): … |
| SST-2 question: sentiment of a movie review | Milyen hangvételű ez a filmkritika? |
| MASSIVE intents: social_post / lists_remove / play_radio | bejegyzés_közzététele_a_közösségi_médiában / elem_törlése_listából / rádió_bekapcsolása |
| "prefer Reader for reads" (Fresh policy) | olvasáshoz az Olvasó eszközt válaszd — the label stays in the nominative ("Olvasó eszközt"), never inflected ("Olvasót"), so it appears verbatim |

Label values inside policy text must match `labels.<group>` exactly; the model has to output them. Machine-readable ids such as intents are lowercase with underscores (`kártya_aktiválása`).
