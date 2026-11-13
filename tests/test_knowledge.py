from pathlib import Path

from app.knowledge import BM25, Doc, KnowledgeBase, chunk, load_docs

KNOWLEDGE = Path(__file__).parent.parent / "knowledge"


def test_loads_sample_docs():
    titles = [d.title for d in load_docs(KNOWLEDGE)]
    assert titles == ["expense-policy.md", "faq.md", "travel-policy.md"]


def test_chunk_respects_size_and_numbers_titles():
    doc = Doc("big.md", "\n\n".join(f"Paragraph {i} " + "x" * 300 for i in range(20)))
    parts = chunk(doc, size=1000, overlap=100)
    assert len(parts) > 3
    assert parts[0].title == "big.md #1"
    assert all(len(p.text) < 1500 for p in parts)


def test_bm25_ranks_relevant_chunk_first():
    docs = [Doc("a", "hotel nights limit city"), Doc("b", "receipt deadline fourteen days"), Doc("c", "lunch")]
    assert BM25(docs).search("How many days to submit a receipt?", k=2)[0].title == "b"


def test_small_corpus_uses_full_context_mode():
    kb = KnowledgeBase(load_docs(KNOWLEDGE), full_context_max_chars=100_000)
    assert kb.full_context and len(kb.passages("anything", 2)) == 3


def test_large_corpus_switches_to_retrieval():
    kb = KnowledgeBase(load_docs(KNOWLEDGE), full_context_max_chars=10)
    hits = kb.passages("per diem international trips", 2)
    assert not kb.full_context and hits[0].title.startswith("travel-policy.md")
