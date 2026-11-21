"""Безопасные инструменты ИИ-консультанта.

Инструменты работают только внутри knowledge/ и не дают доступ к .env,
скрытым файлам, абсолютным путям и произвольной файловой системе.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import storage

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = (BASE_DIR / "knowledge").resolve()

ALLOWED_SUFFIXES = {".md", ".txt"}

# Только эти инструменты доступны модели через function calling.
# save_confirmed_lead модели НЕ выдаётся — она вызывается только из
# confirmation flow после явного подтверждения пользователя.
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Искать по базе знаний мастерской (services.md, faq.md, rules.md). Возвращает файл и фрагмент с совпадением.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Строка для поиска, например «цена посуды» или «сроки»."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_knowledge_file",
            "description": "Прочитать файл из knowledge/ по относительному пути, например «services.md».",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Относительный путь к файлу внутри knowledge/."}
                },
                "required": ["relative_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_lead_draft",
            "description": "Подготовить черновик заявки. Только формирует черновик, НЕ сохраняет заявку. Вызывать, когда известны услуга, описание задачи и контакт.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string", "description": "Подходящая услуга из каталога."},
                    "problem_text": {"type": "string", "description": "Краткое описание задачи пользователя."},
                    "contact": {"type": "string", "description": "Контакт, который оставил пользователь."},
                    "summary": {"type": "string", "description": "Короткая выжимка исходного запроса пользователя."},
                    "missing": {"type": "string", "description": "Чего не хватает для выполнения заявки, либо «ничего»."},
                },
                "required": ["service", "problem_text", "contact", "summary", "missing"],
            },
        },
    },
]


def _safe_resolve(relative_path: str) -> Path | None:
    """Возвращает путь внутри knowledge/ или None, если доступ запрещён."""
    if not relative_path or not isinstance(relative_path, str):
        return None

    candidate = Path(relative_path)

    # Абсолютные пути запрещены.
    if candidate.is_absolute():
        return None

    # Переходы вверх, скрытые файлы и .env запрещены.
    for part in candidate.parts:
        if part in ("", ".", "..") or part.startswith("."):
            return None

    resolved = (KNOWLEDGE_DIR / candidate).resolve()

    # Файл обязан лежать строго внутри knowledge/.
    try:
        resolved.relative_to(KNOWLEDGE_DIR)
    except ValueError:
        return None

    return resolved


def search_knowledge(query: str) -> dict[str, Any]:
    """Поиск по базе знаний. Только внутри knowledge/."""
    query_lower = (query or "").strip().lower()
    if not query_lower:
        return {"found": False, "message": "Пустой поисковый запрос."}

    matches: list[dict[str, Any]] = []
    for file in sorted(KNOWLEDGE_DIR.rglob("*")):
        if not file.is_file() or file.suffix not in ALLOWED_SUFFIXES:
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if query_lower in line.lower():
                snippet = "\n".join(text.splitlines()[max(0, line_no - 2) : line_no + 1])
                matches.append({"file": file.name, "line": line_no, "snippet": snippet})
                break

    if not matches:
        return {"found": False, "message": "В базе знаний ничего не найдено по этому запросу."}

    return {"found": True, "results": matches[:8]}


def read_knowledge_file(relative_path: str) -> dict[str, Any]:
    """Прочитать файл из knowledge/. Запрещены .env, скрытые файлы и пути вне knowledge/."""
    resolved = _safe_resolve(relative_path)
    if resolved is None:
        return {
            "error": "Доступ запрещён: можно читать только файлы внутри knowledge/ "
            "(без .env, скрытых файлов и абсолютных путей)."
        }
    if not resolved.exists() or not resolved.is_file():
        return {"error": f"Файл «{relative_path}» не найден в базе знаний."}

    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        return {"error": f"Не удалось прочитать файл: {exc}"}

    return {"file": resolved.name, "content": content}


def prepare_lead_draft(
    session: dict[str, Any],
    service: str,
    problem_text: str,
    contact: str,
    summary: str,
    missing: str,
) -> dict[str, Any]:
    """Сформировать черновик заявки (без сохранения)."""
    draft = {
        "service": (service or "").strip(),
        "problem_text": (problem_text or "").strip(),
        "contact": (contact or "").strip(),
        "summary": (summary or "").strip(),
        "missing": (missing or "").strip() or "ничего",
    }
    session["ai_draft"] = draft
    return {
        "status": "draft_prepared",
        "message": "Черновик заявки готов. Пользователь должен подтвердить его, изменить или отменить.",
        "draft": draft,
    }


def save_confirmed_lead(session: dict[str, Any]) -> dict[str, Any]:
    """Сохранить подтверждённый черновик в leads с source=ai_consultant."""
    draft = session.get("ai_draft")
    if not draft:
        return {"error": "Нет черновика для сохранения."}

    lead_id = storage.save_lead(
        session_id=session["id"],
        source="ai_consultant",
        service=draft.get("service") or None,
        contact=draft.get("contact") or None,
        problem_text=draft.get("problem_text") or None,
        agent_summary=draft.get("summary") or None,
        missing_info=draft.get("missing") or None,
        status="new",
    )
    session["ai_draft"] = None
    return {"status": "saved", "lead_id": lead_id}


def execute_tool(session: dict[str, Any], name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Диспетчер инструментов, доступных модели."""
    if name == "search_knowledge":
        return search_knowledge(args.get("query", ""))
    if name == "read_knowledge_file":
        return read_knowledge_file(args.get("relative_path", ""))
    if name == "prepare_lead_draft":
        return prepare_lead_draft(
            session,
            service=args.get("service", ""),
            problem_text=args.get("problem_text", ""),
            contact=args.get("contact", ""),
            summary=args.get("summary", ""),
            missing=args.get("missing", ""),
        )
    return {"error": f"Неизвестный инструмент: {name}"}


def dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)
