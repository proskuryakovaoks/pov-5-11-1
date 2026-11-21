"""Генерация скриншотов для evidence/screenshots/ (локальная проверка).

Запуск:
    python dev/take_screenshots.py

Требуется запущенное приложение (http://127.0.0.1:8000) и, для скриншота
ИИ-консультанта, доступный AI Studio (реальный ключ в .env или mock:
    python dev/mock_openai.py).
"""

from __future__ import annotations

import html
import sqlite3
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent.parent
SCREENSHOTS = BASE / "evidence" / "screenshots"
APP_URL = "http://127.0.0.1:8000"

SCREENSHOTS.mkdir(parents=True, exist_ok=True)


def capture_chat(page, name: str) -> None:
    page.evaluate(
        """
        () => {
          const chat = document.querySelector('.chat');
          chat.style.height = 'auto';
          chat.style.minHeight = '640px';
          const msgs = document.querySelector('.chat__messages');
          msgs.style.overflow = 'visible';
          msgs.style.maxHeight = 'none';
        }
        """
    )
    page.wait_for_timeout(250)
    page.locator(".chat").screenshot(path=str(SCREENSHOTS / name))


def quick(page, label: str) -> None:
    page.locator(".quick").filter(has_text=label).first.click()
    page.wait_for_timeout(600)


def type_msg(page, text: str) -> None:
    page.fill("#input", text)
    page.click("#send")
    page.wait_for_timeout(600)


def ensure_text(page, text: str) -> None:
    page.wait_for_selector(f".msg--bot:has-text('{text}')", timeout=10000)


def sqlite_output() -> str:
    lines: list[str] = []
    db = BASE / "data" / "bot.sqlite3"
    for title, sql in [
        ("leads", "SELECT id, source, service, contact, status FROM leads ORDER BY id;"),
        ("feedback", "SELECT id, session_id, message_text, created_at FROM feedback ORDER BY id;"),
    ]:
        lines.append(f"$ sqlite3 data/bot.sqlite3 '{sql}'")
        lines.append(f"-- таблица {title} --")
        out = subprocess.run(
            ["sqlite3", str(db), "-header", "-column", sql],
            capture_output=True,
            text=True,
        )
        lines.append(out.stdout.rstrip() or "(пусто)")
        lines.append("")
    return "\n".join(lines)


def capture_terminal(page, name: str) -> None:
    content = sqlite_output()
    body = html.escape(content)
    page.set_content(
        f"""
        <!doctype html><html><head><meta charset="utf-8"><style>
        body {{ margin:0; background:#1e1e1e; color:#d4d4d4; font-family: Menlo, Monaco, monospace; padding: 28px; }}
        .bar {{ color:#888; font-size:13px; margin-bottom:18px; }}
        .bar b {{ color:#fff; }}
        pre {{ margin:0; line-height:1.5; font-size:14px; white-space: pre-wrap; }}
        </style></head><body>
        <div class="bar"><b>oksana@mac</b> ~/pov-5-11-1</div>
        <pre>{body}</pre>
        </body></html>
        """
    )
    page.wait_for_timeout(250)
    page.screenshot(path=str(SCREENSHOTS / name), full_page=True)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 780, "height": 900})
        page.goto(APP_URL)
        page.wait_for_timeout(800)

        # 01 — главное меню и поле ввода.
        ensure_text(page, "Выберите пункт меню")
        capture_chat(page, "01-local-main-chat.png")

        # 02 — обычный bot-flow: услуги + заявка.
        quick(page, "Услуги")
        ensure_text(page, "Наши услуги")
        quick(page, "Оставить заявку")
        quick(page, "1. Посуда на заказ")
        type_msg(page, "Нужна кружка с логотипом на заказ")
        type_msg(page, "Анна, +7 900 000-00-00")
        ensure_text(page, "Заявка принята")
        capture_chat(page, "02-local-bot-flow.png")

        # Обратная связь (для таблицы feedback).
        quick(page, "Обратная связь")
        type_msg(page, "Очень понравился мастер-класс, спасибо!")
        ensure_text(page, "Обратная связь сохранена")

        # 03 — ИИ-консультант: ответ по базе знаний + черновик заявки.
        quick(page, "ИИ-консультант")
        ensure_text(page, "ИИ-консультант мастерской")
        type_msg(page, "Сколько стоит посуда на заказ?")
        ensure_text(page, "По базе знаний")
        type_msg(page, "Помоги оформить заявку: нужна кружка с логотипом, свяжитесь в Telegram @anna")
        ensure_text(page, "Черновик заявки")
        capture_chat(page, "03-local-ai-consultant.png")

        # Подтверждаем черновик → source=ai_consultant.
        page.locator(".draft__action", has_text="Отправить заявку").click()
        page.wait_for_timeout(600)
        ensure_text(page, "Заявка сохранена")

        # 04 — данные сохранились в SQLite.
        capture_terminal(page, "04-local-database-proof.png")

        browser.close()

    print("Скриншоты готовы:")
    for f in sorted(SCREENSHOTS.glob("*.png")):
        print(" ", f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
