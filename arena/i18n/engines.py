"""Machine translation engines for translated dataset slots.

  manual   writes the pending texts for a human (or any external tool) and stops; `tm import` reads them back
  opus-mt  Helsinki-NLP Marian models through transformers (optional extra: uv sync --frozen --extra dev --extra i18n)
  deepl    DeepL REST API v2 (DEEPL_API_KEY; keys ending in ":fx" use the Free endpoint)
  google   Google Cloud Translation v2 (GOOGLE_TRANSLATE_API_KEY, sent as a header, never in the URL)
  fake     tests only: "[<tgt>] <text>"

API keys are read from the environment (.env is loaded by arena.config) and never logged or repr'd.
"""
from __future__ import annotations
import os
import re
from importlib.util import find_spec
from pathlib import Path
from typing import Callable, Protocol
import httpx

I18N_EXTRA = "uv sync --frozen --extra dev --extra i18n"
# Pinned model revisions (resolved 2026-10-04 with HfApi().model_info(repo).sha).
OPUS_MT_REVISIONS = {"Helsinki-NLP/opus-mt-en-hu": "f2ee4d3f21c0ec85db4eb55d00b3ecc55fbd9d9b"}
# Inputs over SPLIT_TOKENS are split on sentence boundaries. The brief suggested ~400, but the en-hu model silently drops
# content on chunks that long (a 392-token chunk came back at ~54% of the source length; 200/120/60 kept 98-109%).
OPUS_MT_BATCH, OPUS_MT_MAX_LENGTH, OPUS_MT_SPLIT_TOKENS = 16, 512, 200
DEEPL_FREE, DEEPL_PRO = "https://api-free.deepl.com/v2/translate", "https://api.deepl.com/v2/translate"
GOOGLE = "https://translation.googleapis.com/language/translate/v2"
FREE_TIER_NOTE = "DeepL API Free and Google Cloud Translation each include 500,000 characters per month free of charge."

class Engine(Protocol):
    name: str; model: str; revision: str
    def translate(self, texts: list[str], src: str, tgt: str) -> list[str]: ...

class EngineError(RuntimeError):
    """A translation request failed."""

class Unavailable(Exception):
    """A slot cannot be translated right now (no engine, pending manual work, no English source). prepare skips it."""

class EngineUnavailable(Unavailable, EngineError):
    """The engine is not usable here: missing optional dependencies or API key."""

class ManualPending(Unavailable):
    def __init__(self, path: Path, count: int):
        super().__init__(f"{count} texts await manual translation in {path}; translate them and run `tm import`")
        self.path, self.count = path, count

class FakeEngine:
    name = model = "fake"; revision = "0"
    def translate(self, texts, src, tgt): return [f"[{tgt}] {t}" for t in texts]

class ManualEngine:
    name = model = "manual"; revision = ""
    def __init__(self): self.pending_path: Path | None = None
    def translate(self, texts, src, tgt):
        if self.pending_path is None: raise EngineError("manual engine needs a pending file path")
        from arena.i18n.memory import src_sha, write_jsonl
        write_jsonl(self.pending_path, ({"src_sha256": src_sha(t), "src": t} for t in texts))
        raise ManualPending(self.pending_path, len(texts))

_SENTENCE = re.compile(r"(?<=[.!?;:])\s+")

def split_long(text: str, count: Callable[[str], int], limit: int = OPUS_MT_SPLIT_TOKENS) -> list[str]:
    """Split text into pieces of at most `limit` tokens on sentence boundaries (words as a last resort). " ".join(pieces) == text
    for single-spaced text."""
    if count(text) <= limit: return [text]
    pieces, current = [], ""
    def units(sentence):
        if count(sentence) <= limit: return [sentence]
        out, cur = [], ""
        for word in sentence.split():
            trial = f"{cur} {word}" if cur else word
            if cur and count(trial) > limit: out.append(cur); cur = word
            else: cur = trial
        return out + ([cur] if cur else [])
    for sentence in (s for s in _SENTENCE.split(text.strip()) if s):
        for unit in units(sentence):
            trial = f"{current} {unit}" if current else unit
            if current and count(trial) > limit: pieces.append(current); current = unit
            else: current = trial
    return pieces + ([current] if current else [])

class OpusMTEngine:
    name = "opus-mt"
    def __init__(self):
        absent = [m for m in ("transformers", "sentencepiece", "torch") if find_spec(m) is None]
        if absent: raise EngineUnavailable(f"opus-mt needs {', '.join(absent)}: run `{I18N_EXTRA}` (the i18n extra conflicts with --extra abcd)")
        self.model, self.revision, self._loaded = "Helsinki-NLP/opus-mt", "", {}

    def _load(self, src, tgt):
        repo = f"Helsinki-NLP/opus-mt-{src}-{tgt}"
        revision = OPUS_MT_REVISIONS.get(repo)
        if revision is None: raise EngineUnavailable(f"opus-mt: no pinned revision for {repo}; add it to OPUS_MT_REVISIONS in arena/i18n/engines.py")
        if repo not in self._loaded:
            from transformers import MarianMTModel, MarianTokenizer
            try:
                tokenizer = MarianTokenizer.from_pretrained(repo, revision=revision)
                model = MarianMTModel.from_pretrained(repo, revision=revision); model.eval()
            except (OSError, ValueError) as e: raise EngineError(f"opus-mt: cannot load {repo}@{revision[:12]}: {type(e).__name__}") from None
            self._loaded[repo] = (tokenizer, model)
        self.model, self.revision = repo, revision
        return self._loaded[repo]

    def translate(self, texts, src, tgt):
        import torch
        tokenizer, model = self._load(src, tgt)
        count = lambda s: len(tokenizer(s, add_special_tokens=True, truncation=False, verbose=False)["input_ids"])
        plans, segments = [], {}
        for text in texts:  # lines are translated separately and rejoined; long lines are split on sentence boundaries
            plan = []
            for line in text.split("\n"):
                pieces = split_long(line, count) if line.strip() else []
                for piece in pieces: segments.setdefault(piece, None)
                plan.append(pieces)
            plans.append(plan)
        todo = list(segments)
        for i in range(0, len(todo), OPUS_MT_BATCH):
            batch = todo[i:i + OPUS_MT_BATCH]
            encoded = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=OPUS_MT_MAX_LENGTH)
            with torch.no_grad(): output = model.generate(**encoded, max_length=OPUS_MT_MAX_LENGTH)
            for source, target in zip(batch, tokenizer.batch_decode(output, skip_special_tokens=True)): segments[source] = target.strip()
        return ["\n".join(" ".join(segments[p] for p in pieces) for pieces in plan) for plan in plans]

def _key(var: str, engine: str) -> str:
    key = os.environ.get(var, "").strip()
    if not key: raise EngineUnavailable(f"{engine} needs {var} in the environment or .env")
    return key

def _check(response: httpx.Response, engine: str) -> dict:
    if response.status_code != 200:
        detail = response.text[:200].replace("\n", " ")
        raise EngineError(f"{engine}: HTTP {response.status_code}: {detail}")
    return response.json()

class _HTTPEngine:
    batch = 50; var = ""; label = ""
    def __init__(self, client: httpx.Client | None = None):
        self._key = _key(self.var, self.label)
        self._client = client or httpx.Client(timeout=120)
    def __repr__(self): return f"<{type(self).__name__} model={self.model}>"  # never the key
    def translate(self, texts, src, tgt):
        out = []
        for i in range(0, len(texts), self.batch):
            chunk = texts[i:i + self.batch]
            try: result = self._request(chunk, src, tgt)
            except httpx.HTTPError as e: raise EngineError(f"{self.label}: {type(e).__name__}") from None
            if len(result) != len(chunk): raise EngineError(f"{self.label}: expected {len(chunk)} translations, got {len(result)}")
            out.extend(result)
        return out

class DeepLEngine(_HTTPEngine):
    name = "deepl"; revision = "v2"; var = "DEEPL_API_KEY"; label = "DeepL"
    def __init__(self, client=None):
        super().__init__(client)
        free = self._key.endswith(":fx")
        self.url, self.model = (DEEPL_FREE, "deepl-free") if free else (DEEPL_PRO, "deepl-pro")
    def _request(self, chunk, src, tgt):
        response = self._client.post(self.url, headers={"Authorization": f"DeepL-Auth-Key {self._key}"},
                                     json={"text": chunk, "source_lang": src.upper(), "target_lang": tgt.upper(), "preserve_formatting": True})
        return [t["text"] for t in _check(response, self.label)["translations"]]

class GoogleEngine(_HTTPEngine):
    name = "google"; model = "google-nmt"; revision = "v2"; var = "GOOGLE_TRANSLATE_API_KEY"; label = "Google Translate"; batch = 100
    def _request(self, chunk, src, tgt):
        response = self._client.post(GOOGLE, headers={"X-Goog-Api-Key": self._key}, json={"q": chunk, "source": src, "target": tgt, "format": "text"})
        return [t["translatedText"] for t in _check(response, self.label)["data"]["translations"]]

ENGINES: dict[str, Callable[[], Engine]] = {"manual": ManualEngine, "opus-mt": OpusMTEngine, "deepl": DeepLEngine, "google": GoogleEngine, "fake": FakeEngine}
PUBLIC = [name for name in ENGINES if name != "fake"]

def get(name: str) -> Engine:
    if name not in ENGINES: raise ValueError(f"unknown engine {name!r}; choose one of {', '.join(PUBLIC)}")
    return ENGINES[name]()
