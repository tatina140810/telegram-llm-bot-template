"""Builds the Claude request and turns the reply into Telegram text with sources."""
import logging
from dataclasses import dataclass

import anthropic

from app.knowledge import Doc

log = logging.getLogger(__name__)

SYSTEM = (
    "You answer questions for a company's employees using only the attached documents. "
    "If the documents do not contain the answer, say so plainly and suggest who to ask. "
    "Answer in the language of the question. Be concise: short paragraphs or a short list, "
    "no Markdown headings."
)
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass
class Answer:
    text: str
    sources: list[str]


def document_blocks(passages: list[Doc], cache: bool) -> list[dict]:
    blocks = [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": d.text},
            "title": d.title,
            "citations": {"enabled": True},
        }
        for d in passages
    ]
    if cache and blocks:
        # Everything up to and including the last document is a stable prefix:
        # repeat questions pay ~10% of the input price for it.
        blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return blocks


def build_request(model: str, effort: str, max_tokens: int, passages: list[Doc],
                  cache_docs: bool, history: list[dict], question: str) -> dict:
    docs = document_blocks(passages, cache_docs)
    intro = {"type": "text", "text": "Reference documents for this conversation are attached above."}
    messages = [
        {"role": "user", "content": [*docs, intro]},
        {"role": "assistant", "content": "Understood. I will answer from these documents."},
        *history,
        {"role": "user", "content": question},
    ]
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": SYSTEM,
        "messages": messages,
        "output_config": {"effort": effort},
        # If a safety classifier declines, the API retries on a suitable model in the same call.
        "betas": [FALLBACK_BETA],
        "fallbacks": "default",
    }


def parse(response) -> Answer:
    if response.stop_reason == "refusal":
        return Answer("Sorry, I can't help with that request.", [])
    parts, sources = [], []
    for block in response.content:
        if block.type != "text":
            continue
        parts.append(block.text)
        for c in block.citations or []:
            title = c.document_title.split(" #")[0] if c.document_title else None
            if title and title not in sources:
                sources.append(title)
    return Answer("".join(parts).strip(), sources)


class Claude:
    def __init__(self, client: anthropic.AsyncAnthropic, model: str, effort: str, max_tokens: int):
        self.client, self.model, self.effort, self.max_tokens = client, model, effort, max_tokens

    async def ask(self, passages: list[Doc], cache_docs: bool, history: list[dict], question: str) -> Answer:
        req = build_request(self.model, self.effort, self.max_tokens, passages, cache_docs, history, question)
        try:
            response = await self.client.beta.messages.create(**req)
        except anthropic.RateLimitError:
            return Answer("Too many requests right now, please try again in a minute.", [])
        except (anthropic.APIConnectionError, anthropic.InternalServerError):
            return Answer("The AI service is temporarily unavailable. Please try again.", [])
        u = response.usage
        log.info("claude request_id=%s in=%s cache_read=%s cache_write=%s out=%s",
                 response._request_id, u.input_tokens, u.cache_read_input_tokens,
                 u.cache_creation_input_tokens, u.output_tokens)
        return parse(response)
