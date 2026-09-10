#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Создаю окружение…"
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi

if [ ! -f .env ]; then
  echo "Нет файла .env – скопируйте .env.example и впишите ключ."
  echo "Без ключа приложение тоже работает, но разбор будет по правилам."
fi

echo "ReCoin: http://127.0.0.1:8420"
exec ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8420 "$@"
