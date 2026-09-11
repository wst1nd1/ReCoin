"""Отправка писем с кодом восстановления пароля.

Поддерживаются два способа.

Первый – обычные веб-запросы к почтовому сервису (Brevo). Работает по тому же
порту, что и любой сайт, поэтому проходит у провайдеров, закрывающих почтовые
порты, и на бесплатных тарифах хостингов, где исходящая почта запрещена.

Второй – прямое соединение с почтовым сервером по SMTP, например Gmail.

Если не настроен ни один, письмо не уходит, а код пишется в журнал сервера,
чтобы восстановление можно было проверить при разработке.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage

log = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
REQUEST_TIMEOUT = 20

# Куда приходят отзывы из приложения.
FEEDBACK_TO = os.getenv("FEEDBACK_TO") or "thewasteland983@gmail.com"


def _brevo_config() -> dict[str, str] | None:
    key = (os.getenv("BREVO_API_KEY") or "").strip()
    sender = (os.getenv("MAIL_FROM") or os.getenv("SMTP_FROM") or "").strip()
    if not key or not sender:
        return None
    return {"key": key, "sender": sender, "name": (os.getenv("MAIL_FROM_NAME") or "ReCoin").strip()}


def _smtp_config() -> dict[str, str] | None:
    host = (os.getenv("SMTP_HOST") or "").strip()
    if not host:
        return None
    return {
        "host": host,
        "port": (os.getenv("SMTP_PORT") or "587").strip(),
        "user": (os.getenv("SMTP_USER") or "").strip(),
        "password": os.getenv("SMTP_PASSWORD") or "",
        "sender": (os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "").strip(),
    }


def transport() -> str:
    """Каким способом уйдёт письмо."""
    if _brevo_config():
        return "brevo"
    if _smtp_config():
        return "smtp"
    return "none"


def smtp_configured() -> bool:
    """Настроена ли отправка хоть каким-то способом."""
    return transport() != "none"


def _compose(code: str, name: str, lang: str = "ru") -> tuple[str, str]:
    """Тема и текст письма с кодом. Язык выбирает пользователь на сайте."""
    if lang == "en":
        greeting = f"Hello, {name}." if name else "Hello."
        subject = "ReCoin password recovery"
        body = (
            f"{greeting}\n\n"
            f"Your password reset code: {code}\n\n"
            f"The code is valid for 15 minutes. If you did not request a password "
            f"change, simply ignore this message.\n\n"
            f"ReCoin"
        )
        return subject, body

    greeting = f"{name}, здравствуйте." if name else "Здравствуйте."
    subject = "Восстановление пароля в ReCoin"
    body = (
        f"{greeting}\n\n"
        f"Код для смены пароля: {code}\n\n"
        f"Код действует 15 минут. Если вы не запрашивали смену пароля, "
        f"просто не отвечайте на это письмо.\n\n"
        f"ReCoin"
    )
    return subject, body


def _send_via_brevo(to: str, subject: str, body: str,
                    attachment: tuple[str, bytes] | None = None) -> bool:
    settings = _brevo_config()

    letter = {
        "sender": {"name": settings["name"], "email": settings["sender"]},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    if attachment:
        name, data = attachment
        letter["attachment"] = [{"name": name, "content": base64.b64encode(data).decode()}]

    payload = json.dumps(letter).encode("utf-8")

    request = urllib.request.Request(
        BREVO_URL,
        data=payload,
        headers={
            "api-key": settings["key"],
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as exc:
        # Тело ответа содержит причину отказа, она нужна для настройки.
        detail = exc.read().decode("utf-8", "replace")[:300]
        log.warning("Почтовый сервис отклонил письмо на %s: %s %s", to, exc.code, detail)
        return False
    except (urllib.error.URLError, OSError) as exc:
        log.warning("Письмо на %s не отправлено: %s", to, exc)
        return False


def _send_via_smtp(to: str, subject: str, body: str,
                   attachment: tuple[str, bytes] | None = None) -> bool:
    settings = _smtp_config()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["sender"]
    message["To"] = to
    message.set_content(body)

    if attachment:
        name, data = attachment
        subtype = name.rsplit(".", 1)[-1].lower() if "." in name else "octet-stream"
        message.add_attachment(data, maintype="image", subtype=subtype, filename=name)

    try:
        port = int(settings["port"])
        if port == 465:
            with smtplib.SMTP_SSL(settings["host"], port, timeout=REQUEST_TIMEOUT,
                                  context=ssl.create_default_context()) as server:
                if settings["user"]:
                    server.login(settings["user"], settings["password"])
                server.send_message(message)
        else:
            with smtplib.SMTP(settings["host"], port, timeout=REQUEST_TIMEOUT) as server:
                server.starttls(context=ssl.create_default_context())
                if settings["user"]:
                    server.login(settings["user"], settings["password"])
                server.send_message(message)
    except (smtplib.SMTPException, OSError, ValueError) as exc:
        log.warning("Письмо на %s не отправлено: %s", to, exc)
        return False

    return True


def _deliver(to: str, subject: str, body: str,
             attachment: tuple[str, bytes] | None = None) -> bool:
    how = transport()
    if how == "brevo":
        return _send_via_brevo(to, subject, body, attachment)
    if how == "smtp":
        return _send_via_smtp(to, subject, body, attachment)
    return False


def send_reset_code(to: str, code: str, name: str = "", lang: str = "ru") -> bool:
    """Отправить код. False, если письмо не ушло."""
    subject, body = _compose(code, name, lang)
    if _deliver(to, subject, body):
        return True

    # Пока доставка не налажена, код записывается в журнал сервера, иначе
    # он пропадает и сменить пароль становится нечем.
    log.warning("Письмо не доставлено. Код восстановления для %s: %s", to, code)
    return False


def send_feedback(text: str, author: str, attachment: tuple[str, bytes] | None = None,
                  lang: str = "ru") -> bool:
    """Переслать отзыв пользователя."""
    if lang == "en":
        body = f"Feedback from ReCoin\n\nFrom: {author}\n\n{text}\n"
        return _deliver(FEEDBACK_TO, "ReCoin feedback", body, attachment)

    body = f"Отзыв из ReCoin\n\nОт кого: {author}\n\n{text}\n"
    return _deliver(FEEDBACK_TO, "Отзыв о ReCoin", body, attachment)
