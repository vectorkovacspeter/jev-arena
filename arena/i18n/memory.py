"""Translation memory: one JSONL file per language and slot, .arena/translations/<lang>/<slot>.jsonl.

One row per source text: {src_sha256, src, tgt, engine, model, revision, at, reviewed}. New translations are
appended (an interrupted run resumes where it stopped and nothing is translated twice); review edits and imports
rewrite the file atomically. Translated text is third-party derived data and is never committed.
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Iterable
from arena.config import DATA, digest

TRANSLATIONS = DATA / "translations"
FIELDS = ("src_sha256", "src", "tgt", "engine", "model", "revision", "at", "reviewed")

def src_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def lang_dir(lang: str) -> Path:
    return TRANSLATIONS / lang  # module global read at call time so tests can monkeypatch it

def pending_path(lang: str, slot: str) -> Path:
    return lang_dir(lang) / f"{slot}.pending.jsonl"

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    temp.replace(path)

class TranslationMemory:
    def __init__(self, lang: str, slot: str):
        self.lang, self.slot = lang, slot
        self.path = lang_dir(lang) / f"{slot}.jsonl"
        self._rows: dict[str, dict] = {}
        if self.path.exists():
            for row in read_jsonl(self.path): self._rows[row["src_sha256"]] = row  # last row wins

    def __len__(self) -> int: return len(self._rows)

    def rows(self) -> list[dict]: return list(self._rows.values())

    def row(self, src: str) -> dict | None: return self._rows.get(src_sha(src))

    def get(self, src: str) -> str | None:
        row = self.row(src)
        return row["tgt"] if row else None

    def missing(self, texts: Iterable[str]) -> list[str]:
        """Texts without a translation, deduplicated, in first-seen order."""
        seen, out = set(), []
        for text in texts:
            sha = src_sha(text)
            if sha in seen or sha in self._rows: continue
            seen.add(sha); out.append(text)
        return out

    def put_many(self, rows: Iterable[dict]) -> int:
        """Append new translations ({src, tgt, engine, model, revision[, reviewed]}); sources already stored are skipped."""
        new = []
        for r in rows:
            sha = src_sha(r["src"])
            if sha in self._rows: continue
            if not isinstance(r.get("tgt"), str): raise ValueError(f"{self.slot}: translation of {r['src'][:40]!r} is not text")
            row = {"src_sha256": sha, "src": r["src"], "tgt": r["tgt"], "engine": r.get("engine", ""), "model": r.get("model", ""),
                   "revision": r.get("revision", ""), "at": r.get("at") or _now(), "reviewed": bool(r.get("reviewed", False))}
            self._rows[sha] = row; new.append(row)
        if new:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in new))
        return len(new)

    def update(self, src: str, tgt: str | None = None, reviewed: bool | None = None) -> None:
        row = self.row(src)
        if row is None: raise KeyError(f"{self.slot}: no translation for {src[:40]!r}")
        if tgt is not None: row["tgt"] = tgt; row["at"] = _now()
        if reviewed is not None: row["reviewed"] = reviewed
        self._save()

    def _save(self) -> None:
        write_jsonl(self.path, self._rows.values())

    def sha256(self) -> str:
        return digest(self.path.read_bytes()) if self.path.exists() else digest(b"")

    def export(self, path) -> int:
        write_jsonl(Path(path), self._rows.values())
        return len(self._rows)

    def import_(self, path) -> int:
        """Read {src_sha256, tgt[, src, reviewed, engine, model, revision]} rows. Sources missing from a row are looked up in
        the memory and in the manual pending file. Imported rows replace existing translations; `reviewed` is kept."""
        pending = pending_path(self.lang, self.slot)
        known = {r["src_sha256"]: r["src"] for r in read_jsonl(pending)} if pending.exists() else {}
        known.update({sha: r["src"] for sha, r in self._rows.items()})
        count = 0
        for r in read_jsonl(path):
            sha = r.get("src_sha256") or (src_sha(r["src"]) if "src" in r else None)
            src = r.get("src") or known.get(sha)
            if src is None or src_sha(src) != sha: raise ValueError(f"{Path(path).name}: unknown source {sha} (no src and not pending)")
            if not isinstance(r.get("tgt"), str) or not r["tgt"]: raise ValueError(f"{Path(path).name}: empty translation for {sha}")
            old = self._rows.get(sha, {})
            self._rows[sha] = {"src_sha256": sha, "src": src, "tgt": r["tgt"], "engine": r.get("engine") or "manual",
                               "model": r.get("model", ""), "revision": r.get("revision", ""),
                               "at": r.get("at") or _now(), "reviewed": bool(r.get("reviewed", old.get("reviewed", False)))}
            count += 1
        self._save()
        return count
