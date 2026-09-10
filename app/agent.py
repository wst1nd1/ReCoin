"""Слой модели: категоризация непонятных мерчантов, вопросы и разбор.

В модель уходят только названия торговых точек и агрегированные суммы.
Ни ФИО, ни номера карт, ни номера счетов, ни телефоны контрагентов
за пределы машины не отправляются.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path

from . import mcc as M
from .config import build_client, get_settings

log = logging.getLogger(__name__)

# Разобранные мерчанты складываются на диск: названия магазинов не являются
# персональными данными, а повторный разбор одного и того же – трата денег.
CACHE_PATH = Path(__file__).resolve().parent.parent / "merchant_cache.json"

MAX_MERCHANTS_PER_CALL = 120


def _load_cache() -> dict[str, str]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    try:
        CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        log.warning("не удалось сохранить кэш мерчантов: %s", exc)


_CATEGORIZE_TOOL = {
    "name": "save_categories",
    "description": "Сохранить категории для списка торговых точек",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "merchant": {
                            "type": "string",
                            "description": "Название точки ровно как во входном списке",
                        },
                        "category": {
                            "type": "string",
                            "enum": M.ALL_EXPENSE_CATEGORIES,
                        },
                        "note": {
                            "type": "string",
                            "description": "Что это за место, 2-4 слова по-русски",
                        },
                    },
                    "required": ["merchant", "category", "note"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    },
}

_CATEGORIZE_PROMPT = """Ты разбираешь названия торговых точек из банковской выписки \
российского банка и определяешь категорию расходов для каждой.

Названия приходят как есть из платёжной системы: латиницей, с сокращениями, \
кодами городов и мусором вроде «CP*», «YM*», «IP», «OOO». Узнавай российские \
сети и сервисы: DNS и Ситилинк – электроника, Avito и Ozon – маркетплейсы, \
LISSKINS, FUNPAY, case-battle, Tradeit – торговля внутриигровыми предметами, \
«Кубышка» – накопительный счёт.

Правила:
- «Ставки» – букмекеры (BetBoom, Fonbet, Winline, «Лига Ставок») и ЦУПИС/CUPIS: \
это платёжный центр, через который идут все переводы в легальные конторы.
- «Спортзал» – фитнес-клубы и бассейны (DDX, World Class, Alex Fitness).
- «Развлечения» – кино, клубы, бани, игры, внутриигровые покупки, досуг.
- «Прочее» ставь только если действительно невозможно понять, что это.
- Аптеки и клиники – «Здоровье», даже если в названии есть ИП.
- Небольшие ИП с едой (пекарни, кофе, шаурма) – «Кафе и рестораны».
- Магазины у дома, супермаркеты, алкомаркеты – «Продукты».
- Электроника, маркетплейсы, товары для дома, мебель – «Прочее», это разовые покупки.

Верни результат вызовом save_categories для всех точек из списка."""


def categorize_merchants(merchants: list[str]) -> dict[str, str]:
    """Названия точек → категории. Пустой словарь, если модель недоступна."""
    if not merchants:
        return {}

    cache = _load_cache()
    unknown = [m for m in merchants if m not in cache]
    resolved = {m: cache[m] for m in merchants if m in cache}

    if not unknown:
        return resolved

    client = build_client()
    if client is None:
        return resolved

    settings = get_settings()
    import anthropic

    for start in range(0, len(unknown), MAX_MERCHANTS_PER_CALL):
        batch = unknown[start : start + MAX_MERCHANTS_PER_CALL]
        listing = "\n".join(f"- {name}" for name in batch)
        try:
            response = client.messages.create(
                model=settings.model,
                max_tokens=16000,
                thinking={"type": "adaptive"},
                # Узнать сеть по названию – простая задача, глубокое размышление
                # здесь только добавляет минуты ожидания.
                output_config={"effort": "low"},
                system=_CATEGORIZE_PROMPT,
                tools=[_CATEGORIZE_TOOL],
                messages=[{
                    "role": "user",
                    "content": f"Определи категории для точек:\n{listing}",
                }],
            )
        except anthropic.AuthenticationError:
            log.warning("ключ не принят сервисом – категоризация пропущена")
            break
        except anthropic.RateLimitError:
            log.warning("превышен лимит запросов")
            break
        except anthropic.APIStatusError as exc:
            log.warning("сервис ответил ошибкой %s", exc.status_code)
            break
        except anthropic.APIConnectionError:
            log.warning("нет связи с сервисом модели")
            break

        for block in response.content:
            if block.type != "tool_use":
                continue
            payload = block.input if isinstance(block.input, dict) else json.loads(block.input)
            for item in payload.get("items", []):
                name = item.get("merchant")
                category = item.get("category")
                if name in batch and category in M.ALL_EXPENSE_CATEGORIES:
                    cache[name] = category
                    resolved[name] = category

    _save_cache(cache)
    return resolved


_QUESTIONS_TOOL = {
    "name": "save_questions",
    "description": "Сохранить вопросы пользователю о его тратах",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "text": {
                            "type": "string",
                            "description": "Вопрос с конкретными суммами из данных",
                        },
                        "hint": {
                            "type": "string",
                            "description": "Короткое пояснение, зачем это спрашивается",
                        },
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "3-4 варианта быстрого ответа",
                        },
                    },
                    "required": ["id", "text", "hint", "options"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["questions"],
        "additionalProperties": False,
    },
}

_QUESTIONS_PROMPT = """Ты финансовый аналитик. По сводке трат составь 4 вопроса \
пользователю, ответы на которые нужны, чтобы дать ему точный совет.

Требования к вопросам:
- Каждый опирается на конкретную цифру из сводки, а не на общие слова.
- Спрашивай о том, чего нет в выписке: цели, намерения, обязательность трат, \
планы. Не спрашивай то, что и так видно из данных.
- Формулируй нейтрально, без осуждения и морализаторства.
- Обращайся на «вы», пиши по-русски, живым языком.

Верни результат вызовом save_questions."""


def generate_questions(summary: dict) -> list[dict]:
    """Вопросы под конкретные цифры пользователя. Пустой список – если ИИ недоступен."""
    client = build_client()
    if client is None:
        return []

    settings = get_settings()
    import anthropic

    try:
        response = client.messages.create(
            model=settings.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            system=_QUESTIONS_PROMPT,
            tools=[_QUESTIONS_TOOL],
            messages=[{
                "role": "user",
                "content": "Сводка трат:\n" + json.dumps(summary, ensure_ascii=False, indent=1),
            }],
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        log.warning("вопросы не получены: %s", exc)
        return []

    for block in response.content:
        if block.type == "tool_use":
            payload = block.input if isinstance(block.input, dict) else json.loads(block.input)
            return payload.get("questions", [])
    return []


_REPORT_TOOL = {
    "name": "save_report",
    "description": "Сохранить разбор финансов пользователя",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "Оценка финансовой грамотности от 0 до 100",
            },
            "score_reason": {"type": "string", "description": "Из чего сложилась оценка"},
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 сильные стороны с цифрами",
            },
            "problems": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 проблемы с цифрами",
            },
            "advice": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "text": {"type": "string"},
                        "saving_per_year": {
                            "type": "integer",
                            "description": "Оценка экономии в рублях за год, 0 если неприменимо",
                        },
                    },
                    "required": ["title", "text", "saving_per_year"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["score", "score_reason", "strengths", "problems", "advice"],
        "additionalProperties": False,
    },
}

_REPORT_PROMPT = """Ты финансовый консультант. По сводке трат и ответам пользователя \
составь разбор его финансового поведения.

Правила:
- Опирайся только на предоставленные данные, не выдумывай сумм.
- Советы должны быть выполнимыми и конкретными: что именно сделать, а не \
«ведите бюджет» и «тратьте меньше».
- Экономию считай честно от реальных цифр, не завышай.
- Учитывай, что переводы между своими счетами и возвращённые долги не являются тратами.
- Если долг по кредитной карте растёт – это главная проблема, скажи прямо.
- Пиши на «вы», по-русски, без морализаторства и без похвалы ради похвалы.
- Не давай инвестиционных рекомендаций и не советуй конкретные финансовые продукты.

Верни результат вызовом save_report."""


def build_report(summary: dict, answers: dict[str, str]) -> dict | None:
    """Итоговый разбор. None, если модель недоступна."""
    client = build_client()
    if client is None:
        return None

    settings = get_settings()
    import anthropic

    payload = {
        "сводка": summary,
        "ответы_пользователя": answers,
    }

    try:
        with client.messages.stream(
            model=settings.model,
            max_tokens=32000,
            thinking={"type": "adaptive"},
            # На «максимуме» разбор занимал до пяти минут при том же качестве
            # выводов – столько ждать никто не станет.
            output_config={"effort": "medium"},
            system=_REPORT_PROMPT,
            tools=[_REPORT_TOOL],
            messages=[{
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, indent=1),
            }],
        ) as stream:
            response = stream.get_final_message()
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        log.warning("разбор не получен: %s", exc)
        return None

    for block in response.content:
        if block.type == "tool_use":
            return block.input if isinstance(block.input, dict) else json.loads(block.input)
    return None
