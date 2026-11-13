"""Ask the knowledge base from a terminal — no Telegram needed.

    python -m app.cli "How many days do I have to submit a receipt?"
"""
import asyncio
import sys

from app.config import get_settings
from app.factory import build_service
from app.service import render


async def main(question: str) -> None:
    service = build_service(get_settings())
    print(render(await service.ask(0, question)))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    asyncio.run(main(" ".join(sys.argv[1:])))
