"""Настройки приложения и клиент модели."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# override=True принципиально: в окружении, откуда запускают приложение, могут
# быть свои ANTHROPIC_* (например, у разработчика в терминале), и без этого
# флага они молча победят настройки из .env, а запросы уйдут не туда.
load_dotenv(override=True)

DEFAULT_MODEL = "claude-opus-5"


@dataclass(frozen=True)
class Settings:
    base_url: str | None
    auth_token: str | None
    api_key: str | None
    model: str
    https_only: bool

    @property
    def ai_available(self) -> bool:
        return bool(self.auth_token or self.api_key)


def get_settings() -> Settings:
    return Settings(
        base_url=os.getenv("ANTHROPIC_BASE_URL") or None,
        auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN") or None,
        api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        model=os.getenv("RECOIN_MODEL") or DEFAULT_MODEL,
        # На хостинге сайт работает по HTTPS, и сессионную куку нужно помечать
        # флагом secure. Локально запуск идёт по HTTP, где такая кука браузером
        # отбрасывается, поэтому режим включается переменной окружения.
        https_only=os.getenv("RECOIN_HTTPS", "").strip().lower() in {"1", "true", "yes"},
    )


def build_client():
    """Клиент Anthropic. None, если ключей нет – тогда работает режим без ИИ.

    Прокси-сервисы обычно принимают заголовок Authorization: Bearer, что в SDK
    задаётся параметром auth_token; прямой доступ к Anthropic использует x-api-key.
    """
    settings = get_settings()
    if not settings.ai_available:
        return None

    import anthropic

    kwargs: dict[str, object] = {}
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    if settings.auth_token:
        kwargs["auth_token"] = settings.auth_token
    else:
        kwargs["api_key"] = settings.api_key

    return anthropic.Anthropic(**kwargs)
