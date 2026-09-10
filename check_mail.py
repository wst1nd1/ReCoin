"""Проверка отправки писем.

Запуск: .venv/bin/python check_mail.py [адрес получателя]

Без аргумента письмо уходит на адрес отправителя из настроек.
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)

from app import mailer  # noqa: E402  – настройки должны загрузиться раньше

logging.basicConfig(level=logging.WARNING, format="%(message)s")

NAMES = {
    "brevo": "почтовый сервис Brevo, обычные веб-запросы",
    "smtp": "прямое соединение с почтовым сервером",
}


def main() -> int:
    how = mailer.transport()
    if how == "none":
        print("Отправка не настроена.")
        print("Заполните BREVO_API_KEY и MAIL_FROM либо SMTP_HOST в файле .env.")
        return 1

    sender = os.getenv("MAIL_FROM") or os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or ""
    to = sys.argv[1] if len(sys.argv) > 1 else sender

    print(f"Способ   {NAMES[how]}")
    print(f"От кого  {sender}")
    print(f"Кому     {to}")
    print("Отправляю…")

    if mailer.send_reset_code(to, "123456", "Проверка"):
        print("Письмо отправлено. Проверьте входящие и папку со спамом.")
        return 0

    print("Отправить не удалось. Причина указана выше.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
