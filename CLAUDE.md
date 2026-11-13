# telegram-llm-bot-template — notes for contributors and AI assistants

- `app/knowledge.py` loads `knowledge/*.md|*.txt`; small corpus → whole, cached; large → BM25 chunks.
- `app/llm.py` builds the Claude request (documents with citations, prompt caching, server-side fallbacks).
- `app/service.py` is transport-agnostic; `app/bot.py` (aiogram) and `app/cli.py` are thin adapters.
- Tests: `pytest -q` (no network; Claude is faked). Keep files under 300 lines. Never commit `.env`.
