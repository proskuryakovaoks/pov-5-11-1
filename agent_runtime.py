"""Цикл ИИ-консультанта: роль из agent/soul.md + безопасные tools.

Консультант отвечает только по knowledge/, при необходимости вызывает tools
(search_knowledge, read_knowledge_file, prepare_lead_draft) и готовит черновик
заявки. Сохранение заявки происходит отдельно — только после подтверждения
пользователя (см. confirm/edit/cancel ниже).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import ai_client
import bot_flow
from agent import tools

logger = logging.getLogger("agent_runtime")

BASE_DIR = Path(__file__).resolve().parent
SOUL_PATH = BASE_DIR / "agent" / "soul.md"

MAX_LOOP = 6

AI_GREETING = (
    "Я — ИИ-консультант мастерской «Глина». Задайте вопрос об услугах, ценах или сроках, "
    "и я отвечу по материалам мастерской. Могу помочь выбрать услугу и подготовить черновик заявки."
)

DRAFT_FALLBACK_REPLY = "Вот черновик вашей заявки. Подтвердите его, измените или отмените."


def _load_soul() -> str:
    return SOUL_PATH.read_text(encoding="utf-8")


def _parse_args(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _assistant_message(msg: Any) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": getattr(msg, "content", None)}
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        message["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ]
    return message


def _history(session: dict[str, Any]) -> list[dict[str, Any]]:
    return session.setdefault("ai_history", [])


def start(session: dict[str, Any]) -> dict[str, Any]:
    session["mode"] = "ai"
    _history(session)
    session.pop("ai_draft", None)
    return {"reply": AI_GREETING, "quick_replies": ["Назад в меню"]}


def handle(session: dict[str, Any], text: str) -> dict[str, Any]:
    text = (text or "").strip()

    if text.lower() in ("назад в меню", "меню", "главное меню", "назад"):
        session["mode"] = "menu"
        session.pop("ai_draft", None)
        return bot_flow.menu_message()

    _history(session).append({"role": "user", "content": text})
    messages: list[dict[str, Any]] = [{"role": "system", "content": _load_soul()}] + _history(session)

    msg = _call(messages)
    if msg is None:
        return {
            "reply": "Не удалось получить ответ от ИИ-консультанта. Попробуйте ещё раз.",
            "quick_replies": ["Назад в меню"],
        }

    for _ in range(MAX_LOOP):
        if getattr(msg, "tool_calls", None):
            messages.append(_assistant_message(msg))
            for tool_call in msg.tool_calls:
                args = _parse_args(tool_call.function.arguments)
                result = tools.execute_tool(session, tool_call.function.name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tools.dumps(result),
                    }
                )
            msg = _call(messages)
            if msg is None:
                return {
                    "reply": "Не удалось получить ответ от ИИ-консультанта. Попробуйте ещё раз.",
                    "quick_replies": ["Назад в меню"],
                }
            continue

        reply = (getattr(msg, "content", "") or "").strip()
        _history(session).append({"role": "assistant", "content": reply or DRAFT_FALLBACK_REPLY})

        draft = session.get("ai_draft")
        if draft:
            return {
                "reply": reply or DRAFT_FALLBACK_REPLY,
                "draft": draft,
                "quick_replies": [],
            }
        return {"reply": reply or DRAFT_FALLBACK_REPLY, "quick_replies": ["Назад в меню"]}

    return {
        "reply": "Не удалось завершить консультацию за один заход. Переформулируйте вопрос.",
        "quick_replies": ["Назад в меню"],
    }


def _call(messages: list[dict[str, Any]]) -> Any:
    try:
        return ai_client.chat(messages, tools=tools.TOOL_DEFINITIONS)
    except RuntimeError as exc:
        logger.info("AI unavailable: %s", exc)
        return _UnavailableMessage(str(exc))
    except Exception as exc:  # noqa: BLE001 — не раскрываем детали в UI
        logger.warning("AI call failed: %s", type(exc).__name__)
        return _UnavailableMessage("ошибка вызова AI Studio API")


class _UnavailableMessage:
    """Заглушка сообщения, чтобы вернуть пользователю понятную причину отказа."""

    def __init__(self, reason: str) -> None:
        self.content = f"ИИ-консультант сейчас недоступен: {reason}"
        self.tool_calls = None


def confirm(session: dict[str, Any]) -> dict[str, Any]:
    result = tools.save_confirmed_lead(session)
    if result.get("status") == "saved":
        session["mode"] = "menu"
        return {
            "reply": f"Заявка сохранена (№ {result['lead_id']}). Мы свяжемся с вами в ближайшее время.",
            "quick_replies": bot_flow.QUICK_MENU,
        }
    # Сохранить не удалось: остаёмся в консультации и объясняем причину.
    session["mode"] = "ai"
    return {
        "reply": result.get("message") or "Не удалось сохранить заявку.",
        "quick_replies": ["Назад в меню"],
    }


def edit(session: dict[str, Any]) -> dict[str, Any]:
    session.pop("ai_draft", None)
    session["mode"] = "ai"
    return {"reply": "Хорошо. Что нужно уточнить или изменить в заявке?", "quick_replies": ["Назад в меню"]}


def cancel(session: dict[str, Any]) -> dict[str, Any]:
    session.pop("ai_draft", None)
    session["mode"] = "menu"
    return {"reply": "Заявка отменена. Черновик не сохранён.", "quick_replies": bot_flow.QUICK_MENU}
