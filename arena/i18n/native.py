"""Config-driven importer for native-language datasets pinned on the Hugging Face Hub.

A slot in locales/<lang>/datasets.yaml names the repo, revision, files, columns and label mapping.
Rows are pooled across files, filtered (drop_labels), sampled with the importers' stratified algorithm,
and turned into localized choice cases whose labels come from prompts.yaml. Never executes dataset scripts.
"""
from __future__ import annotations
import csv
import io
import json
import re
from pathlib import Path
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
from arena.config import DATASETS, digest
from arena.contracts import Case, Question
from arena.i18n.datasets import Slot
from arena.i18n.packs import stratified
from arena.i18n.prompts import labels, prompt

RESERVED = ("label", "id")  # fields that are not state text

def download(lang: str, slot: Slot, name: str) -> Path:
    local = DATASETS / lang / "raw" / slot.repo.replace("/", "--")
    return Path(hf_hub_download(slot.repo, name, repo_type="dataset", revision=slot.revision, local_dir=local))

QUOTED = re.compile(r'"(?:[^"]|"")*"', re.S)

def unquote(value):
    """One unescape pass for cells that are CSV-quoted twice, as in SIB-200's TSV.

    After the csv reader such a cell is still one complete quoted field (it starts and ends with a quote
    and every inner quote is doubled); ordinary text with quotes inside never matches."""
    if isinstance(value, str) and len(value) >= 2 and QUOTED.fullmatch(value):
        return value[1:-1].replace('""', '"')
    return value

def read_rows(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".parquet": return pq.read_table(path).to_pylist()
    text = path.read_bytes().decode("utf-8")  # no newline translation: the csv reader handles quoted line breaks
    if suffix in (".tsv", ".csv"):
        reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t" if suffix == ".tsv" else ",")
        return [{key: unquote(value) for key, value in row.items()} for row in reader]
    if suffix == ".jsonl": return [json.loads(line) for line in text.splitlines() if line.strip()]
    if suffix == ".json":
        try: data = json.loads(text)
        except json.JSONDecodeError: return [json.loads(line) for line in text.splitlines() if line.strip()]
        if isinstance(data, dict) and isinstance(data.get("data"), list): data = data["data"]
        if not isinstance(data, list): raise ValueError(f"{path.name}: expected a list of rows")
        return data
    raise ValueError(f"{path.name}: unsupported file type {suffix}")

def split_name(name: str) -> str:
    """'data/val.json' -> 'val'; 'hu-HU/test/0000.parquet' -> 'test'."""
    p = Path(name)
    return p.parent.name if p.stem.isdigit() and p.parent.name else p.stem

def build(lang: str, slot_id: str, slot: Slot) -> list[Case]:
    if slot.source != "native": raise ValueError(f"{slot_id}: not a native slot")
    for name in ("label_group", "question", "sample"):
        if getattr(slot, name) is None: raise ValueError(f"{slot_id}: native build needs {name}")
    if "label" not in slot.fields: raise ValueError(f"{slot_id}: fields need a label column")
    if not slot.state and "text" not in slot.fields: raise ValueError(f"{slot_id}: fields need a text column or a state template")
    group = labels(lang, slot.label_group)
    question_text = prompt(lang, slot.question)
    rows, hashes = [], {}
    for name in slot.files:
        path = download(lang, slot, name)
        hashes[name] = digest(path.read_bytes())
        split = split_name(name)
        for index, row in enumerate(read_rows(path)):
            raw = row.get(slot.fields["label"])
            if raw is None: raise ValueError(f"{slot_id}: unlabelled row {split}:{index} (use labelled splits only)")
            raw = str(raw)
            if raw in slot.drop_labels: continue
            label_id = slot.source_label_ids.get(raw, raw) if slot.source_label_ids else raw
            if (slot.source_label_ids and raw not in slot.source_label_ids) or label_id not in group:
                raise ValueError(f"{slot_id}: label {raw!r} has no id in labels.{slot.label_group}")
            source_index = str(row[slot.fields["id"]]) if "id" in slot.fields else str(index)
            rows.append({"row": row, "label": label_id, "raw": raw, "split": split, "index": source_index})
    if len(slot.files) > 1: keys = [f"{r['split']}-{r['index']}" for r in rows]
    else: keys = [r["index"] for r in rows]
    label_ids = {localized: stable for stable, localized in group.items()}
    options = list(group.values())
    cases = []
    for i in stratified(rows, slot.sample, seed=slot.seed):
        r, key = rows[i], keys[i]
        values = {name: r["row"][column] for name, column in slot.fields.items() if name not in RESERVED}
        state = prompt(lang, slot.state, **values) if slot.state else values["text"]
        cid = f"{lang}:{slot_id}-{key}"
        provenance = {"source": f"https://huggingface.co/datasets/{slot.repo}", "repo": slot.repo, "revision": slot.revision, "config": slot.config,
                      "files": hashes, "source_split": r["split"], "source_index": r["index"], "sampling_seed": slot.seed, "licence": slot.licence,
                      "redistribution": "download from original source", "slot": slot_id, "source_label": r["raw"], "label_ids": label_ids}
        cases.append(Case(id=cid, cluster=cid, pack=slot.pack, family=slot.family, language=lang, state=state,
                          question=Question(id=slot.question_id, kind="choice", text=question_text, labels=options),
                          gold=group[r["label"]], label_status="public", provenance=provenance))
    return cases
