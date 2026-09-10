"""Работа без модели: вопросы и разбор на правилах.

Нужен, когда ключа нет, сервис недоступен или кончился баланс. Приложение
обязано оставаться полезным в любом случае – пусть формулировки и суше.
"""

from __future__ import annotations

from decimal import Decimal

from . import mcc as M
from .analytics import Analysis


def _money(value: Decimal | int | float) -> str:
    return f"{int(value):,}".replace(",", " ")


def generate_questions(analysis: Analysis) -> list[dict]:
    """Вопросы по реальным цифрам, отобранные по профилю трат."""
    questions: list[dict] = []
    categories = {row.name: row for row in analysis.categories}

    if analysis.debt_increased > 0:
        questions.append({
            "id": "debt",
            "text": (
                f"За период долг по кредитной карте вырос на "
                f"{_money(analysis.debt_increased)} ₽. Это осознанное решение "
                f"или деньги кончались раньше, чем приходили?"
            ),
            "hint": "От этого зависит, с чего начинать наводить порядок.",
            "options": [
                "Осознанно, пользуюсь беспроцентным периодом",
                "Денег не хватало до зарплаты",
                "Была крупная незапланированная покупка",
                "Не следил за этим",
            ],
        })

    if bets := categories.get(M.BETS):
        questions.append({
            "id": "bets",
            "text": (
                f"На ставки ушло {_money(bets.amount)} ₽ за {bets.count} операций. "
                f"Вы считаете это развлечением с понятным бюджетом?"
            ),
            "hint": "Помогает понять, есть ли у трат предел, который вы себе ставите.",
            "options": [
                "Да, трачу только заранее отложенное",
                "Бюджета нет, играю по настроению",
                "Пытаюсь отыграться",
                "Хочу это прекратить",
            ],
        })

    if cafe := categories.get(M.CAFE):
        questions.append({
            "id": "cafe",
            "text": (
                f"Кафе и доставка – {_money(cafe.amount)} ₽ "
                f"({cafe.share:.0f}% трат, {cafe.count} заказов). "
                f"Это осознанный выбор или чаще выходит спонтанно?"
            ),
            "hint": "Спонтанные заказы – самая простая статья для сокращения.",
            "options": [
                "Осознанно, экономлю время",
                "Чаще спонтанно, когда лень готовить",
                "Обедаю так на работе или учёбе",
                "Хочу сократить",
            ],
        })

    if analysis.regulars:
        total_year = sum((r.per_year for r in analysis.regulars), Decimal(0))
        names = ", ".join(r.merchant for r in analysis.regulars[:3])
        questions.append({
            "id": "regulars",
            "text": (
                f"Нашлись регулярные списания на {_money(total_year)} ₽ в год "
                f"({names}). Всеми пользуетесь?"
            ),
            "hint": "Забытые подписки – самые обидные траты.",
            "options": [
                "Да, всё нужно",
                "Часть можно отключить",
                "Не знал о некоторых",
                "Надо разобраться",
            ],
        })

    if analysis.lent_not_returned > 0:
        questions.append({
            "id": "lent",
            "text": (
                f"Переводы людям на {_money(analysis.lent_not_returned)} ₽ "
                f"не вернулись обратно. Это долги, подарки или оплата чего-то?"
            ),
            "hint": "Долги вернутся, подарки нет – считаются они по-разному.",
            "options": [
                "Одолжил, вернут",
                "Это подарки и помощь",
                "Оплата покупок и услуг",
                "Всё вместе",
            ],
        })

    questions.append({
        "id": "goal",
        "text": "Откладываете ли вы часть дохода и есть ли цель, на которую копите?",
        "hint": "Без цели накопления почти всегда проигрывают спонтанным тратам.",
        "options": [
            "Да, откладываю регулярно",
            "Откладываю, когда остаётся",
            "Не откладываю",
            "Есть цель, но не получается копить",
        ],
    })

    return questions[:5]


def build_report(analysis: Analysis, answers: dict[str, str]) -> dict:
    """Оценка и советы на правилах и порогах."""
    categories = {row.name: row for row in analysis.categories}
    strengths: list[str] = []
    problems: list[str] = []
    advice: list[dict] = []

    score = 60

    # Накопления
    if analysis.saved_to_savings > 0:
        strengths.append(
            f"Вы откладываете деньги: за период на накопительные счета ушло "
            f"{_money(analysis.saved_to_savings)} ₽."
        )
        score += 10
    else:
        problems.append("За период на накопительные счета ничего не отложено.")
        score -= 10

    # Долг
    if analysis.debt_increased > 0:
        problems.append(
            f"Долг по кредитной карте вырос на {_money(analysis.debt_increased)} ₽ – "
            f"вы тратите больше, чем зарабатываете."
        )
        score -= 15
        advice.append({
            "title": "Остановить рост долга",
            "text": (
                f"Долг вырос на {_money(analysis.debt_increased)} ₽. Пока он растёт, "
                f"любые накопления бессмысленны: проценты по карте съедят их быстрее. "
                f"Зафиксируйте сумму долга и гасите её частями, не наращивая новых трат по карте."
            ),
            "saving_per_year": int(analysis.debt_increased),
        })
    elif analysis.debt_repaid > 0:
        strengths.append(f"Вы погасили {_money(analysis.debt_repaid)} ₽ долга.")
        score += 10

    # Необязательные траты
    if analysis.optional_share > 30:
        problems.append(
            f"Необязательные траты – {analysis.optional_share:.0f}% расходов "
            f"({_money(analysis.optional_amount)} ₽)."
        )
        score -= 10
        cut = analysis.optional_amount / 3 / analysis.months * 12
        advice.append({
            "title": "Сократить необязательные траты на треть",
            "text": (
                f"Кафе, развлечения, подписки и одежда забрали "
                f"{_money(analysis.optional_amount)} ₽. Сокращение на треть освободит "
                f"{_money(cut)} ₽ в год без заметной потери качества жизни."
            ),
            "saving_per_year": int(cut),
        })
    elif analysis.optional_share < 15:
        strengths.append(
            f"Необязательные траты держатся на уровне {analysis.optional_share:.0f}% – это немного."
        )
        score += 5

    # Ставки
    if bets := categories.get(M.BETS):
        per_year = bets.amount / analysis.months * 12
        problems.append(f"Ставки забрали {_money(bets.amount)} ₽ за период.")
        score -= 10
        advice.append({
            "title": "Ограничить ставки твёрдым лимитом",
            "text": (
                f"На ставки ушло {_money(bets.amount)} ₽, это {_money(per_year)} ₽ в год. "
                f"Математически такие игры всегда в минус на длинной дистанции. "
                f"Если бросать не готовы – заведите отдельный счёт с фиксированной суммой "
                f"на месяц и не пополняйте его сверх лимита."
            ),
            "saving_per_year": int(per_year),
        })

    # Регулярные платежи
    if analysis.regulars:
        total_year = sum((r.per_year for r in analysis.regulars), Decimal(0))
        advice.append({
            "title": "Проверить регулярные списания",
            "text": (
                f"Регулярные платежи стоят {_money(total_year)} ₽ в год: "
                + ", ".join(f"{r.merchant} ({_money(r.per_year)} ₽/год)" for r in analysis.regulars[:4])
                + ". Отключите то, чем не пользуетесь."
            ),
            "saving_per_year": int(total_year / 3),
        })

    # Доставка и кафе
    if cafe := categories.get(M.CAFE):
        if cafe.share > 12:
            per_year = cafe.amount / analysis.months * 12
            advice.append({
                "title": "Заменить часть доставок готовкой",
                "text": (
                    f"Кафе и доставка – {_money(cafe.amount)} ₽ за {cafe.count} заказов, "
                    f"в среднем {_money(cafe.amount / cafe.count)} ₽ за раз. "
                    f"Даже два домашних ужина в неделю вместо заказа дадут около "
                    f"{_money(per_year / 4)} ₽ в год."
                ),
                "saving_per_year": int(per_year / 4),
            })

    # Невозвращённые долги
    if analysis.lent_not_returned > 0:
        problems.append(
            f"{_money(analysis.lent_not_returned)} ₽ ушло людям и не вернулось."
        )

    if not advice:
        advice.append({
            "title": "Держать текущий курс",
            "text": (
                "Явных проблем в тратах не видно. Полезно завести цель накопления "
                "и откладывать фиксированную сумму сразу после поступления денег."
            ),
            "saving_per_year": 0,
        })

    if not strengths:
        strengths.append(
            f"Траты собраны и разобраны по категориям – "
            f"{_money(analysis.living_expense)} ₽ за период видно целиком."
        )

    score = max(5, min(95, score))

    return {
        "score": score,
        "score_reason": (
            "Оценка собрана из доли необязательных трат, наличия накоплений, "
            "динамики долга и регулярных платежей."
        ),
        "strengths": strengths,
        "problems": problems or ["Существенных проблем не обнаружено."],
        "advice": advice[:5],
        "offline": True,
    }
