"""Provider health check, independent of the LLM router.

Answers two questions per provider, using your real keys:
  1. Which model ids exist for this key?
  2. Does a streaming call return a first token within TIMEOUT seconds?

Run from the backend/ folder (it reads backend/.env):
    uv run python ../scripts/check_providers.py

Optional overrides: CHECK_GEMINI_MODEL, CHECK_GROQ_MODEL, CHECK_OPENAI_MODEL
"""

import asyncio
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(".env"))

TIMEOUT = 15
PROMPT = "Reply with the single word: OK"
SKIP = ("exp", "preview", "image", "tts", "live", "lite", "thinking", "embedding")


async def first_token(make_stream) -> float:
    """Seconds until the first non-empty text chunk, or raise."""
    start = time.perf_counter()
    async with asyncio.timeout(TIMEOUT):
        async for text in make_stream():
            if text:
                return time.perf_counter() - start
    raise RuntimeError("stream ended without any text")


async def check_gemini() -> None:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    names = await asyncio.to_thread(lambda: [m.name for m in client.models.list()])
    gemini = [n.removeprefix("models/") for n in names if "gemini" in n]
    print(f"  models ({len(gemini)}): {', '.join(gemini[:12])}")
    # Use gemini-3.8-flash as it's recommended by Google for new users
    preferred = "gemini-3-flash-preview"
    model = os.environ.get("CHECK_GEMINI_MODEL") or (
        preferred if preferred in gemini else next(
            (n for n in gemini if "flash" in n and not any(s in n for s in SKIP)), gemini[0]
        )
    )

    async def stream():
        events = await client.aio.models.generate_content_stream(
            model=model,
            contents=PROMPT,
            config=types.GenerateContentConfig(max_output_tokens=10),
        )
        async for chunk in events:
            yield chunk.text

    print(f"  testing model: {model}")
    print(f"  time to first token: {await first_token(stream):.2f}s")


async def check_groq() -> None:
    from groq import AsyncGroq

    client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
    ids = [m.id for m in (await client.models.list()).data]
    print(f"  models ({len(ids)}): {', '.join(ids[:12])}")
    # Use qwen3.8-27b as it's a working chat model for streaming
    preferred = "qwen/qwen3.8-27b"
    model = os.environ.get("CHECK_GROQ_MODEL") or (preferred if preferred in ids else ids[0])

    async def stream():
        events = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": PROMPT}],
            stream=True,
            max_tokens=10,
        )
        async for ev in events:
            yield ev.choices[0].delta.content if ev.choices else None

    print(f"  testing model: {model}")
    print(f"  time to first token: {await first_token(stream):.2f}s")


async def check_openai() -> None:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    ids = sorted(m.id for m in (await client.models.list()).data)
    chat = [i for i in ids if i.startswith("gpt-")]
    print(f"  models ({len(chat)} gpt-*): {', '.join(chat[:12])}")
    model = os.environ.get("CHECK_OPENAI_MODEL") or "gpt-4o-mini"

    async def stream():
        events = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": PROMPT}],
            stream=True,
            max_tokens=10,
        )
        async for ev in events:
            yield ev.choices[0].delta.content if ev.choices else None

    print(f"  testing model: {model}")
    print(f"  time to first token: {await first_token(stream):.2f}s")


CHECKS = [
    ("gemini", "GEMINI_API_KEY", check_gemini),
    ("groq", "GROQ_API_KEY", check_groq),
    ("openai", "OPENAI_API_KEY", check_openai),
]


async def main() -> None:
    for name, key_var, check in CHECKS:
        print(f"\n[{name}]")
        if not os.environ.get(key_var):
            print(f"  skipped: {key_var} is not set")
            continue
        try:
            await check()
        except TimeoutError:
            print(f"  FAILED: no first token within {TIMEOUT}s (this is your hang)")
        except Exception as exc:  # report the real provider error, whatever it is
            print(f"  FAILED: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())