import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import get_settings
from app.factory import build_service
from app.ratelimit import RateLimiter
from app.service import QAService, render, split_for_telegram

log = logging.getLogger(__name__)


def make_router(service: QAService, limiter: RateLimiter, allowed: set[int], max_chars: int) -> Router:
    router = Router()

    def permitted(m: Message) -> bool:
        return not allowed or (m.from_user is not None and m.from_user.id in allowed)

    @router.message(CommandStart())
    async def start(m: Message) -> None:
        if permitted(m):
            await m.answer("Hi! Ask me anything about the company handbook. /reset starts a new conversation.")

    @router.message(Command("reset"))
    async def reset(m: Message) -> None:
        service.reset(m.chat.id)
        await m.answer("Conversation cleared.")

    @router.message(F.text)
    async def question(m: Message) -> None:
        if not permitted(m):
            return
        if not limiter.allow(m.from_user.id if m.from_user else m.chat.id):
            await m.answer("You're sending messages too fast. Please wait a minute.")
            return
        if len(m.text) > max_chars:
            await m.answer(f"Please keep questions under {max_chars} characters.")
            return
        await m.bot.send_chat_action(m.chat.id, ChatAction.TYPING)
        answer = await service.ask(m.chat.id, m.text)
        for part in split_for_telegram(render(answer)):
            await m.answer(part)

    return router


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    s = get_settings()
    if not s.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    service = build_service(s)
    log.info("knowledge base: %d docs, mode=%s", len(service.kb.docs),
             "full-context (cached)" if service.kb.full_context else "bm25 retrieval")
    dp = Dispatcher()
    dp.include_router(make_router(service, RateLimiter(s.rate_limit_per_minute), s.allowed_ids, s.max_question_chars))
    await dp.start_polling(Bot(s.telegram_bot_token))


if __name__ == "__main__":
    asyncio.run(main())
