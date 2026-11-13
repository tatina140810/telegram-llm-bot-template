from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    # Read by the Anthropic SDK itself; declared here only so a missing key fails fast.
    anthropic_api_key: str = ""

    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "low"  # chat Q&A rarely needs more; raise for harder corpora
    max_answer_tokens: int = 4000

    knowledge_dir: Path = Path("knowledge")
    # Below this size the whole corpus goes into a cached prompt; above it, BM25 picks chunks.
    full_context_max_chars: int = 400_000
    top_k_chunks: int = 6
    history_turns: int = 6

    allowed_user_ids: str = ""  # comma-separated Telegram ids; empty = anyone
    rate_limit_per_minute: int = 6
    max_question_chars: int = 2000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_ids(self) -> set[int]:
        return {int(x) for x in self.allowed_user_ids.split(",") if x.strip().isdigit()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
