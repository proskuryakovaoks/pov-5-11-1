"""Локальный mock AI Studio (OpenAI-совместимый endpoint) — ТОЛЬКО для проверки без реального ключа.

Позволяет прогнать полный сценарий ИИ-консультанта локально, когда настоящий
AI_STUDIO_API_KEY ещё не настроен. Не входит в production-код и не обязателен
для сдачи: при наличии реального ключа просто заполните .env и работайте с
настоящим API.

Запуск:
    python dev/mock_openai.py

Затем в .env укажите:
    AI_STUDIO_API_KEY=test-key
    AI_STUDIO_BASE_URL=http://127.0.0.1:9999/v1
    AI_STUDIO_MODEL=mock-model
"""

from __future__ import annotations

import json
import re
import uuid

from fastapi import FastAPI, Request

app = FastAPI()

KNOWLEDGE = {
    "посуда": "Керамическая посуда на заказ — от 1 500 ₽ за предмет. Точная цена зависит от размера, сложности и глазури.",
    "декор": "Декор и предметы интерьера — от 3 000 ₽. Вазы, кашпо, подсвечники, панно под ваш размер и цвет.",
    "срок": "Посуда и декор — обычно 2–4 недели. Крупные изделия и мебель — от 4 недель.",
    "гарантия": "Если изделие пришло с дефектом производства — заменим или вернём деньги в течение 14 дней.",
    "мастер-класс": "Мастер-класс по лепке и гончарному кругу — от 2 500 ₽, материалы и обжиг включены.",
}

SERVICE_BY_KEYWORD = [
    ("посуда|кружк|тарелк|чашк|сервиз", "Керамическая посуда на заказ"),
    ("декор|ваз|панно|кашпо|подсвечник", "Декор и предметы интерьера"),
    ("подарочн|набор|сервиз", "Подарочные наборы и сервизы"),
    ("мастер|лепк|гончарн", "Мастер-класс по лепке и гончарному кругу"),
    ("мебел|стол|полк", "Авторская мебель и крупные изделия"),
]


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def _last_tool_result(messages: list[dict]) -> dict | None:
    for m in reversed(messages):
        if m.get("role") == "tool":
            try:
                return json.loads(m.get("content") or "{}")
            except json.JSONDecodeError:
                return {}
    return None


LEAD_WORDS = ("заявк", "помоги", "хочу", "нужн", "оформ", "заказать")


def _is_lead(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in LEAD_WORDS)


def _question_query(text: str) -> str:
    low = text.lower()
    for kw in ("мастер-класс", "посуда", "декор", "набор", "мебел", "срок", "гарантия", "предоплата", "договор", "цена", "стоимость"):
        if kw in low:
            return kw
    return "услуги"


def _detect_service(text: str) -> str:
    for pattern, service in SERVICE_BY_KEYWORD:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return service
    return "Керамическая посуда на заказ"


def _detect_contact(text: str) -> str:
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    if email:
        return email.group(0)
    phone = re.search(r"(\+?\d[\d\-() ]{6,})", text)
    if phone:
        return phone.group(1).strip()
    tg = re.search(r"@[\w_]+", text)
    if tg:
        return tg.group(0)
    return "не указан"


def _message(content: str | None = None, tool_calls: list | None = None) -> dict:
    msg: dict = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def _completion(message: dict, finish_reason: str = "stop") -> dict:
    return {
        "id": "chatcmpl-" + uuid.uuid4().hex[:16],
        "object": "chat.completion",
        "created": 0,
        "model": "mock-model",
        "choices": [
            {"index": 0, "message": message, "finish_reason": finish_reason}
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> dict:
    data = await request.json()
    messages: list[dict] = data.get("messages", [])
    user_text = _last_user_text(messages)
    tool_result = _last_tool_result(messages)

    # Ответ после результата инструмента.
    if tool_result is not None:
        if tool_result.get("status") == "draft_prepared":
            return _completion(
                _message("Вот черновик заявки. Проверьте данные и подтвердите, измените или отмените.")
            )
        if tool_result.get("found") is True:
            results = tool_result.get("results", [])
            snippet = results[0]["snippet"] if results else ""
            return _completion(_message("По базе знаний мастерской: " + snippet.strip()))
        if "content" in tool_result:
            return _completion(_message("По базе знаний: " + tool_result["content"][:400]))
        return _completion(_message("В базе знаний нет точного ответа. Могу помочь подобрать услугу и оформить заявку."))

    # Запрос на заявку.
    if _is_lead(user_text):
        service = _detect_service(user_text)
        contact = _detect_contact(user_text)
        return _completion(
            _message(
                None,
                tool_calls=[
                    {
                        "id": "call_draft",
                        "type": "function",
                        "function": {
                            "name": "prepare_lead_draft",
                            "arguments": json.dumps(
                                {
                                    "service": service,
                                    "problem_text": user_text,
                                    "contact": contact,
                                    "summary": user_text,
                                    "missing": "ничего",
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            ),
            finish_reason="tool_calls",
        )

    # Обычный вопрос — ищем в базе знаний через search_knowledge.
    query = _question_query(user_text)
    return _completion(
        _message(
            None,
            tool_calls=[
                {
                    "id": "call_search",
                    "type": "function",
                    "function": {
                        "name": "search_knowledge",
                        "arguments": json.dumps({"query": query}, ensure_ascii=False),
                    },
                }
            ],
        ),
        finish_reason="tool_calls",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9999)
