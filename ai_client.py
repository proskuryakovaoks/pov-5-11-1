"""Подключение к AI Studio API (OpenAI-совместимый клиент).

Секреты не хранятся в коде и не попадают в логи: ключ читается только из
переменных окружения (`.env`), в логи пишется лишь факт конфигурации.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ai_client")

PLACEHOLDER_KEYS = {"", "put_your_api_key_here", "your_api_key_here", "changeme"}


def _config() -> tuple[str, str, str]:
    api_key = os.getenv("AI_STUDIO_API_KEY", "").strip()
    base_url = os.getenv("AI_STUDIO_BASE_URL", "").strip()
    model = os.getenv("AI_STUDIO_MODEL", "").strip()
    return api_key, base_url, model


def is_configured() -> bool:
    api_key, base_url, model = _config()
    return bool(api_key and api_key.lower() not in PLACEHOLDER_KEYS and base_url and model)


def _client():
    if not is_configured():
        raise RuntimeError(
            "AI Studio API не настроен. Заполните AI_STUDIO_API_KEY, "
            "AI_STUDIO_BASE_URL и AI_STUDIO_MODEL в .env (см. .env.example)."
        )
    api_key, base_url, model = _config()
    from openai import OpenAI

    logger.info("AI Studio: клиент настроен, model=%s", model)
    return OpenAI(api_key=api_key, base_url=base_url), model


def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.2,
) -> Any:
    """Один вызов chat.completions. Возвращает message (content + tool_calls)."""
    client, model = _client()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message
