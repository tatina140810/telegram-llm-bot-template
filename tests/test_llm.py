from types import SimpleNamespace as NS

import pytest

from app.knowledge import Doc
from app.llm import Claude, build_request, parse
from app.service import QAService, render, split_for_telegram

DOCS = [Doc("expense-policy.md", "Submit within 14 days."), Doc("faq.md", "Ask finance.")]


def test_request_caches_documents_and_enables_fallbacks():
    req = build_request("claude-opus-5-5", "low", 4000, DOCS, True, [], "Deadline?")
    blocks = req["messages"][0]["content"]
    assert [b.get("cache_control") for b in blocks[:2]] == [None, {"type": "ephemeral"}]
    assert all(b["citations"] == {"enabled": True} for b in blocks[:2])
    assert req["fallbacks"] == "default" and req["output_config"] == {"effort": "low"}
    assert req["messages"][-1] == {"role": "user", "content": "Deadline?"}


def test_retrieved_passages_are_not_cached():
    req = build_request("m", "low", 10, DOCS, False, [], "q")
    assert all("cache_control" not in b for b in req["messages"][0]["content"])


def cite(title):
    return NS(document_title=title)


def test_parse_collects_unique_sources():
    resp = NS(stop_reason="end_turn", content=[
        NS(type="text", text="Within 14 days", citations=[cite("expense-policy.md #2")]),
        NS(type="text", text=".", citations=[cite("expense-policy.md #1"), cite("faq.md")]),
    ])
    a = parse(resp)
    assert a.text == "Within 14 days." and a.sources == ["expense-policy.md", "faq.md"]
    assert render(a).endswith("Sources: expense-policy.md, faq.md")


def test_refusal_is_handled():
    assert "can't help" in parse(NS(stop_reason="refusal", content=[])).text


def test_split_for_telegram():
    parts = split_for_telegram("line\n" * 2000, limit=4000)
    assert all(len(p) <= 4000 for p in parts) and len(parts) == 3


class FakeMessages:
    def __init__(self):
        self.calls = []

    async def create(self, **kw):
        self.calls.append(kw)
        usage = NS(input_tokens=1, cache_read_input_tokens=0, cache_creation_input_tokens=0, output_tokens=1)
        return NS(stop_reason="end_turn", usage=usage, _request_id="req_test",
                  content=[NS(type="text", text=f"answer {len(self.calls)}", citations=None)])


@pytest.mark.asyncio
async def test_service_keeps_per_chat_history():
    fake = FakeMessages()
    claude = Claude(NS(beta=NS(messages=fake)), "m", "low", 100)
    kb = NS(full_context=True, passages=lambda q, k: DOCS)
    svc = QAService(kb, claude, top_k=3, history_turns=2)
    await svc.ask(1, "first")
    await svc.ask(1, "second")
    await svc.ask(2, "other chat")
    assert [m["content"] for m in fake.calls[1]["messages"][2:]] == ["first", "answer 1", "second"]
    assert len(fake.calls[2]["messages"]) == 3  # chat 2 has no history
