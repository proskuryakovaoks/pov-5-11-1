# Чат-бот мастерской «Глина»

Веб-чат с ботом для мастерской керамики, декора и авторской мебели «Глина».
Один Python-runtime (FastAPI + SQLite), обычный сценарный bot-flow и
ИИ-консультант, который отвечает только по базе знаний компании через AI Studio
API и готовит черновик заявки. Заявка сохраняется только после подтверждения.

Спецификация MVP — в [spec.md](spec.md).

## Что умеет бот

- **Главное меню** — Услуги, FAQ, Оставить заявку, ИИ-консультант, Обратная связь.
- **Услуги** — каталог из 5 услуг с ценой «от …».
- **FAQ** — 4 категории: услуги, стоимость, сроки и формат работы, правила и контакты.
- **Обычная заявка** — сценарный bot-flow без обращения к модели (услуга → задача → контакт), сохраняется в SQLite с `source=bot_flow`.
- **ИИ-консультант** — отвечает по `knowledge/`, помогает выбрать услугу, задаёт 1–2 уточняющих вопроса, готовит черновик заявки (сохраняется с `source=ai_consultant` только после подтверждения).
- **Обратная связь** — сохраняется отдельно от заявок в таблицу `feedback`.

Bot-flow и обратная связь работают даже без AI Studio API-ключа.

## Технологический стек

- Python 3.13.x, venv
- FastAPI + Uvicorn (один runtime)
- SQLite (`data/bot.sqlite3`), создаётся автоматически
- AI Studio API через SDK `openai` (OpenAI-совместимый endpoint)
- Обычные HTML/CSS/JS в `static/`

## Структура проекта

```
app.py              точка входа (FastAPI + раздача static/ + POST /api/chat)
bot_flow.py         сценарный bot-flow (меню, услуги, FAQ, заявка, обратная связь)
ai_client.py        подключение к AI Studio API (без секретов в коде)
agent_runtime.py    цикл ИИ-консультанта (agent loop)
agent/tools.py      безопасные tools консультанта
agent/soul.md       роль, тон и ограничения консультанта
storage.py          SQLite: таблицы leads и feedback
knowledge/          база знаний: services.md, faq.md, rules.md
static/             интерфейс чата (index.html, style.css, app.js)
data/               bot.sqlite3 (создаётся при запуске, не коммитится)
evidence/screenshots/ 5 обязательных скриншотов
spec.md             спецификация MVP
requirements.txt    зависимости
.env.example        пример переменных окружения
dev/                вспомогательные скрипты (mock API, генерация скриншотов)
deploy/             файлы для запуска на VPS
```

## Подготовка окружения (локально)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка .env

```bash
cp .env.example .env
```

Заполните `.env`:

| Переменная | Назначение |
|---|---|
| `AI_STUDIO_API_KEY` | ключ AI Studio API |
| `AI_STUDIO_BASE_URL` | OpenAI-совместимый base URL (например `https://…/v1`) |
| `AI_STUDIO_MODEL` | имя модели |

Необязательные (есть значения по умолчанию): `DB_PATH=data/bot.sqlite3`,
`APP_HOST=127.0.0.1`, `APP_PORT=8000`.

> `.env` не коммитится (`.gitignore`). В репозитории только `.env.example`.
> Без настроенного ключа ИИ-консультант честно сообщит о недоступности API,
> остальной функционал продолжит работать.

## Запуск (локально)

```bash
source .venv/bin/activate
python app.py
```

Откройте http://127.0.0.1:8000.

Остановка — `Ctrl+C`. Повторный запуск — снова `python app.py`.

SQLite инициализируется автоматически при первом запуске (`data/bot.sqlite3`,
таблицы `leads` и `feedback`).

## Сценарий проверки

1. Открыть чат → видно главное меню и поле ввода.
2. **Услуги** → каталог из 5 услуг.
3. **FAQ** → выбрать категорию и прочитать ответы.
4. **Оставить заявку** → выбрать услугу → описать задачу → оставить контакт → «Заявка принята».
5. **Обратная связь** → написать сообщение → сохранено.
6. **ИИ-консультант** → задать вопрос («Сколько стоит посуда на заказ?») → ответ по базе знаний; попросить помочь с заявкой → черновик с действиями «Отправить заявку / Изменить / Отмена».
7. **Отправить заявку** → заявка сохраняется в `leads` с `source=ai_consultant`.

## База данных (SQLite)

Таблица `leads`:

| Поле | Назначение |
|---|---|
| `session_id` | id сессии чата |
| `source` | источник: `bot_flow` или `ai_consultant` |
| `service` | выбранная услуга |
| `contact` | контакт пользователя |
| `problem_text` | описание задачи |
| `agent_summary` | выжимка/исходный запрос (для ИИ-заявки) |
| `missing_info` | чего не хватает (для ИИ-заявки) |
| `status` | статус (по умолчанию `new`) |
| `created_at` | время создания (UTC) |

Таблица `feedback`:

| Поле | Назначение |
|---|---|
| `session_id` | id сессии чата |
| `message_text` | текст отзыва |
| `created_at` | время создания (UTC) |

Диагностика:

```bash
sqlite3 data/bot.sqlite3 -header -column "SELECT id, source, service, contact, status FROM leads;"
sqlite3 data/bot.sqlite3 -header -column "SELECT id, message_text, created_at FROM feedback;"
```

## ИИ-консультант: tools и ограничения

Роль и ограничения описаны в `agent/soul.md`. Доступ к данным — только через
инструменты в `agent/tools.py`:

| Tool | Назначение |
|---|---|
| `search_knowledge` | поиск по базе знаний `knowledge/` |
| `read_knowledge_file` | чтение файла из `knowledge/` (по относительному пути) |
| `prepare_lead_draft` | формирование черновика заявки (без сохранения) |
| `save_confirmed_lead` | сохранение заявки (вызывается только после подтверждения, модели не выдаётся) |

Защита инструментов:

- `read_knowledge_file` не читает `.env`, скрытые файлы, абсолютные пути и файлы вне `knowledge/`;
- консультант не выполняет shell-команды и не работает с произвольной файловой системой;
- консультант не выдумывает цены, сроки, скидки и гарантии, которых нет в `knowledge/`;
- если информации нет — честно говорит об этом и предлагает оставить заявку;
- заявка сохраняется только после явного подтверждения пользователя (черновик создаётся отдельно от сохранения).

## AI Studio: биллинг и лимиты

После первых запросов к LLM проверьте в консоли AI Studio:

- списались ли средства/токены за запросы (биллинг активен и корректен);
- не исчерпан ли лимит запросов или токенов в минуту.

Если лимит исчерпан, ИИ-консультант корректно сообщит об ошибке вызова API —
bot-flow, заявка и обратная связь при этом продолжают работать.

## Запуск на VPS (один runtime)

Код доставляется через git (SourceCraft). На сервере поднимается тот же проект.

### 1. Клонировать репозиторий

```bash
git clone <url-репозитория> ~/glina && cd ~/glina
```

### 2. Виртуальное окружение и зависимости

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Создать .env с реальными значениями

```bash
cp .env.example .env
nano .env   # AI_STUDIO_API_KEY, AI_STUDIO_BASE_URL, AI_STUDIO_MODEL
```

Также на VPS задайте `APP_HOST=0.0.0.0` и нужный `APP_PORT`.

### 4. Запуск как один runtime (systemd)

Пример unit-файла — `deploy/glina.service`. Скопируйте и поправьте пути:

```bash
sudo cp deploy/glina.service /etc/systemd/system/glina.service
sudo systemctl daemon-reload
sudo systemctl enable --now glina
```

### 5. Логи и повторный запуск

```bash
sudo systemctl status glina          # статус
journalctl -u glina -f               # логи в реальном времени
sudo systemctl restart glina         # перезапуск
```

После перезапуска проект снова стартует без ошибок, SQLite подключается по
пути `data/bot.sqlite3` (создаётся автоматически). В логах нет секретов:
пишется только факт конфигурации клиента (имя модели), без ключей.

Проверка, что runtime поднялся:

```bash
curl -s http://127.0.0.1:8000/api/health
```

## Скриншоты

`evidence/screenshots/`:

- `01-local-main-chat.png` — интерфейс чата, меню и поле ввода;
- `02-local-bot-flow.png` — обычный bot-flow (услуги + заявка);
- `03-local-ai-consultant.png` — ИИ-консультант отвечает по базе знаний и готовит черновик;
- `04-local-database-proof.png` — данные сохранились в SQLite;
- `05-vps-runtime-start.png` — проект запущен на VPS без ошибок.

Перегенерировать локальные скриншоты: `python dev/take_screenshots.py`
(требуется запущенное приложение; для ИИ-сценария — настроенный ключ или
`python dev/mock_openai.py`).
