"""Loads the knowledge base and retrieves passages.

Small corpora are sent whole (and cached by the API); large ones are split
into overlapping chunks and ranked with BM25 — no vector DB to run.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_WORD = re.compile(r"\w+", re.UNICODE)
SUPPORTED = {".md", ".txt"}


@dataclass(frozen=True)
class Doc:
    title: str
    text: str


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def load_docs(folder: Path) -> list[Doc]:
    files = sorted(p for p in folder.rglob("*") if p.suffix.lower() in SUPPORTED)
    return [Doc(title=str(p.relative_to(folder)), text=p.read_text(encoding="utf-8")) for p in files]


def chunk(doc: Doc, size: int = 1200, overlap: int = 200) -> list[Doc]:
    """Split on paragraph boundaries into ~size-char chunks with some overlap."""
    paras = [p.strip() for p in doc.text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if buf and len(buf) + len(p) > size:
            chunks.append(buf)
            buf = buf[-overlap:]
        buf = f"{buf}\n\n{p}".strip()
    if buf:
        chunks.append(buf)
    return [Doc(title=f"{doc.title} #{i + 1}", text=c) for i, c in enumerate(chunks)]


class BM25:
    def __init__(self, docs: list[Doc], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.tf = [Counter(tokenize(d.text)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tf]
        self.avg = (sum(self.lens) / len(self.lens)) if docs else 0.0
        df = Counter(term for tf in self.tf for term in tf)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int) -> list[Doc]:
        terms = tokenize(query)
        scored = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t in terms:
                if t in tf:
                    norm = 1 - self.b + self.b * self.lens[i] / self.avg
                    s += self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * norm)
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        return [self.docs[i] for _, i in scored[:k]]


class KnowledgeBase:
    def __init__(self, docs: list[Doc], full_context_max_chars: int):
        self.docs = docs
        self.full_context = sum(len(d.text) for d in docs) <= full_context_max_chars
        self.index = None if self.full_context else BM25([c for d in docs for c in chunk(d)])

    def passages(self, question: str, k: int) -> list[Doc]:
        return self.docs if self.full_context else self.index.search(question, k)
