from __future__ import annotations

import os

import anthropic


_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    """Return a shared Anthropic async client (singleton)."""
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


async def complete(
    prompt: str,
    *,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
    system: str | None = None,
) -> str:
    """Send a single user message and return the text response."""
    client = get_client()
    messages = [{"role": "user", "content": prompt}]
    kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    response = await client.messages.create(**kwargs)
    return response.content[0].text
