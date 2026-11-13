import anthropic

from app.config import Settings
from app.knowledge import KnowledgeBase, load_docs
from app.llm import Claude
from app.service import QAService


def build_service(s: Settings) -> QAService:
    if not s.anthropic_api_key:
        raise SystemExit("ANTHROPIC_API_KEY is not set")
    docs = load_docs(s.knowledge_dir)
    if not docs:
        raise SystemExit(f"No .md/.txt files found in {s.knowledge_dir}")
    kb = KnowledgeBase(docs, s.full_context_max_chars)
    claude = Claude(anthropic.AsyncAnthropic(), s.claude_model, s.claude_effort, s.max_answer_tokens)
    return QAService(kb, claude, s.top_k_chunks, s.history_turns)
