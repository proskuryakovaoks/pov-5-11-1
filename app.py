"""Точка входа: FastAPI + web-интерфейс чата.

Один runtime: раздаёт статику (static/) и обрабатывает POST /api/chat,
маршрутизируя сообщения между сценарным bot-flow и ИИ-консультантом.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import agent_runtime
import bot_flow
import storage

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("app")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

storage.init_db()

app = FastAPI(title="Глина — чат-бот мастерской")

# В памяти: состояние диалога по session_id. Не содержит секретов.
sessions: dict[str, dict] = {}


def _new_session(session_id: str) -> dict:
    return {"id": session_id, "mode": "menu"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(request: Request) -> dict:
    data = await request.json()
    session_id = str(data.get("session_id") or uuid.uuid4())
    text = (data.get("text") or "").strip()

    session = sessions.setdefault(session_id, _new_session(session_id))

    # Действия confirmation flow (черновик заявки ИИ-консультанта).
    if text == "__confirm_lead__":
        return agent_runtime.confirm(session)
    if text == "__edit_lead__":
        return agent_runtime.edit(session)
    if text == "__cancel_lead__":
        return agent_runtime.cancel(session)

    mode = session.get("mode", "menu")

    if mode == "ai":
        return agent_runtime.handle(session, text)

    result = bot_flow.handle(session, text)
    if result.get("switch_to") == "ai":
        result = agent_runtime.start(session)
    return result


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    logger.info("Запуск приложения на %s:%s", host, port)
    uvicorn.run(app, host=host, port=port)
