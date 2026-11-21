#!/usr/bin/env bash
# Развёртывание чат-бота «Глина» на VPS как один runtime.
# Запускать на сервере из директории с репозиторием (git clone/pull).
#
#   bash deploy/setup_vps.sh
#
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_URL="${1:-}"

echo "==> Каталог приложения: $APP_DIR"

if [ -z "$(ls -A "$APP_DIR" 2>/dev/null)" ] && [ -n "$REPO_URL" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "==> Обновление кода"
git pull --ff-only 2>/dev/null || true

echo "==> Виртуальное окружение"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> .env"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env из .env.example — заполните реальные значения (AI_STUDIO_API_KEY, APP_HOST=0.0.0.0 и т.д.)."
fi

echo "==> systemd unit"
sudo cp deploy/glina.service /etc/systemd/system/glina.service
sudo systemctl daemon-reload
sudo systemctl enable --now glina

echo "==> Статус"
sudo systemctl status glina --no-pager || true

echo "==> Проверка"
curl -s http://127.0.0.1:8000/api/health && echo
