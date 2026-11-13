"""Transport-agnostic core: used by the Telegram bot and the CLI alike."""
from collections import defaultdict, deque

from app.knowledge import KnowledgeBase
from app.llm import Answer, Claude


class QAService:
    def __init__(self, kb: KnowledgeBase, claude: Claude, top_k: int, history_turns: int):
        self.kb, self.claude, self.top_k = kb, claude, top_k
        self.history: dict[int, deque] = defaultdict(lambda: deque(maxlen=history_turns * 2))

    def reset(self, chat_id: int) -> None:
        self.history.pop(chat_id, None)

    async def ask(self, chat_id: int, question: str) -> Answer:
        passages = self.kb.passages(question, self.top_k)
        hist = self.history[chat_id]
        answer = await self.claude.ask(passages, self.kb.full_context, list(hist), question)
        hist.append({"role": "user", "content": question})
        hist.append({"role": "assistant", "content": answer.text or "(no answer)"})
        return answer


def render(answer: Answer) -> str:
    if not answer.sources:
        return answer.text
    return f"{answer.text}\n\nSources: " + ", ".join(answer.sources)


def split_for_telegram(text: str, limit: int = 4000) -> list[str]:
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        cut = cut if cut > 0 else limit
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    return parts + [text] if text else parts
