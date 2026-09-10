"""Агрегация разобранных операций в сводку для интерфейса и для модели."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from . import mcc as M
from .categorizer import clean_merchant
from .models import Transaction
from .netting import NettingResult

# Сколько раз должна повториться трата у одного мерчанта, чтобы счесть её регулярной.
REGULAR_MIN_COUNT = 3
# Насколько суммы регулярных списаний могут отличаться (доля от средней).
REGULAR_TOLERANCE = Decimal("0.15")


@dataclass
class CategoryRow:
    name: str
    amount: Decimal
    count: int
    share: float


@dataclass
class MerchantRow:
    name: str
    amount: Decimal
    count: int
    category: str


@dataclass
class MonthRow:
    key: str                 # 2026-08, для сортировки
    label: str               # «Август 2026»
    amount: Decimal
    count: int
    top_category: str
    top_amount: Decimal
    delta: float | None      # изменение к предыдущему месяцу, проценты


@dataclass
class RegularPayment:
    merchant: str
    average: Decimal
    count: int
    category: str
    per_year: Decimal


@dataclass
class Analysis:
    period_start: datetime | None = None
    period_end: datetime | None = None
    months: Decimal = Decimal(1)

    gross_expense: Decimal = Decimal(0)
    net_expense: Decimal = Decimal(0)
    living_expense: Decimal = Decimal(0)   # траты у мерчантов, без переводов
    income: Decimal = Decimal(0)

    categories: list[CategoryRow] = field(default_factory=list)
    top_merchants: list[MerchantRow] = field(default_factory=list)
    biggest: list[Transaction] = field(default_factory=list)
    regulars: list[RegularPayment] = field(default_factory=list)
    monthly: list[tuple[str, Decimal]] = field(default_factory=list)
    months_detail: list[MonthRow] = field(default_factory=list)

    optional_amount: Decimal = Decimal(0)
    optional_share: float = 0.0
    average_check: Decimal = Decimal(0)
    weekend_share: float = 0.0
    transactions_count: int = 0

    saved_to_savings: Decimal = Decimal(0)
    debt_repaid: Decimal = Decimal(0)
    debt_increased: Decimal = Decimal(0)
    lent_not_returned: Decimal = Decimal(0)

    def month_label(self, when: datetime) -> str:
        return f"{when.year}-{when.month:02d}"


_MONTH_NAMES = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]


def _month_label(key: str) -> str:
    """«2026-08» → «Август 2026»."""
    year, month = key.split("-")
    name = _MONTH_NAMES[int(month) - 1]
    return f"{name.capitalize()} {year}"


def _months_between(start: datetime | None, end: datetime | None) -> Decimal:
    if not start or not end:
        return Decimal(1)
    days = (end - start).days
    return max(Decimal(days) / Decimal(30), Decimal("0.5"))


def analyze(
    transactions: list[Transaction],
    netting_result: NettingResult,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> Analysis:
    """Свести операции в готовые для показа цифры."""
    result = Analysis(
        period_start=period_start,
        period_end=period_end,
        months=_months_between(period_start, period_end),
        gross_expense=netting_result.gross_expense,
        net_expense=netting_result.net_expense,
        saved_to_savings=netting_result.saved_to_savings,
        debt_repaid=netting_result.debt_repaid,
        debt_increased=netting_result.debt_increased,
        transactions_count=len(transactions),
    )

    purchases = [t for t in netting_result.purchases if t.amount < 0]
    result.living_expense = sum((t.abs_amount for t in purchases), Decimal(0))
    result.income = netting_result.net_income

    # Невозвращённые долги людям – отдельная строка, это не покупка.
    result.lent_not_returned = sum(
        (p.real_expense for p in netting_result.people()), Decimal(0)
    )

    by_category: dict[str, Decimal] = defaultdict(Decimal)
    count_category: dict[str, int] = defaultdict(int)
    by_merchant: dict[str, Decimal] = defaultdict(Decimal)
    count_merchant: Counter = Counter()
    merchant_category: dict[str, str] = {}
    by_month: dict[str, Decimal] = defaultdict(Decimal)
    count_month: dict[str, int] = defaultdict(int)
    month_categories: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    merchant_amounts: dict[str, list[Decimal]] = defaultdict(list)

    weekend = Decimal(0)

    for tx in purchases:
        by_category[tx.category] += tx.abs_amount
        count_category[tx.category] += 1

        name = clean_merchant(tx.description)
        by_merchant[name] += tx.abs_amount
        count_merchant[name] += 1
        merchant_category[name] = tx.category
        merchant_amounts[name].append(tx.abs_amount)

        month = result.month_label(tx.date)
        by_month[month] += tx.abs_amount
        count_month[month] += 1
        month_categories[month][tx.category] += tx.abs_amount
        if tx.date.weekday() >= 5:
            weekend += tx.abs_amount

    total = result.living_expense or Decimal(1)

    result.categories = sorted(
        (
            CategoryRow(
                name=name,
                amount=amount,
                count=count_category[name],
                share=float(amount / total * 100),
            )
            for name, amount in by_category.items()
        ),
        key=lambda row: row.amount,
        reverse=True,
    )

    result.top_merchants = sorted(
        (
            MerchantRow(
                name=name,
                amount=amount,
                count=count_merchant[name],
                category=merchant_category.get(name, M.OTHER),
            )
            for name, amount in by_merchant.items()
        ),
        key=lambda row: row.amount,
        reverse=True,
    )[:15]

    result.biggest = sorted(purchases, key=lambda t: t.abs_amount, reverse=True)[:8]
    result.monthly = sorted(by_month.items())

    previous: Decimal | None = None
    for key, amount in result.monthly:
        categories_of_month = month_categories[key]
        top_name, top_amount = (
            max(categories_of_month.items(), key=lambda kv: kv[1])
            if categories_of_month else (M.OTHER, Decimal(0))
        )
        delta = None
        if previous and previous > 0:
            delta = float((amount - previous) / previous * 100)
        result.months_detail.append(
            MonthRow(
                key=key,
                label=_month_label(key),
                amount=amount,
                count=count_month[key],
                top_category=top_name,
                top_amount=top_amount,
                delta=delta,
            )
        )
        previous = amount

    result.optional_amount = sum(
        (amount for name, amount in by_category.items() if name in M.OPTIONAL_CATEGORIES),
        Decimal(0),
    )
    result.optional_share = float(result.optional_amount / total * 100)
    result.weekend_share = float(weekend / total * 100)
    if purchases:
        result.average_check = result.living_expense / len(purchases)

    # Регулярные списания: один мерчант, стабильная сумма, несколько повторов.
    regulars: list[RegularPayment] = []
    for name, amounts in merchant_amounts.items():
        if len(amounts) < REGULAR_MIN_COUNT:
            continue
        average = sum(amounts, Decimal(0)) / len(amounts)
        if average <= 0:
            continue
        stable = all(abs(a - average) <= average * REGULAR_TOLERANCE for a in amounts)
        if not stable:
            continue
        per_month = Decimal(len(amounts)) / result.months
        regulars.append(
            RegularPayment(
                merchant=name,
                average=average,
                count=len(amounts),
                category=merchant_category.get(name, M.OTHER),
                per_year=average * per_month * 12,
            )
        )
    result.regulars = sorted(regulars, key=lambda r: r.per_year, reverse=True)[:10]

    return result


def to_summary(analysis: Analysis) -> dict:
    """Компактная сводка для модели.

    Содержит только суммы и названия торговых точек – никаких ФИО,
    номеров карт, счетов и телефонов.
    """
    def money(value: Decimal) -> int:
        return int(value)

    return {
        "период": {
            "с": analysis.period_start.strftime("%d.%m.%Y") if analysis.period_start else None,
            "по": analysis.period_end.strftime("%d.%m.%Y") if analysis.period_end else None,
            "месяцев": float(round(analysis.months, 1)),
        },
        "траты_у_мерчантов_всего": money(analysis.living_expense),
        "траты_в_месяц": money(analysis.living_expense / analysis.months),
        "поступления": money(analysis.income),
        "средний_чек": money(analysis.average_check),
        "операций": analysis.transactions_count,
        "доля_трат_в_выходные_процент": round(analysis.weekend_share, 1),
        "необязательные_траты": money(analysis.optional_amount),
        "доля_необязательных_процент": round(analysis.optional_share, 1),
        "категории": [
            {
                "название": row.name,
                "сумма": money(row.amount),
                "доля_процент": round(row.share, 1),
                "операций": row.count,
            }
            for row in analysis.categories
        ],
        "топ_мерчантов": [
            {
                "название": row.name,
                "сумма": money(row.amount),
                "раз": row.count,
                "категория": row.category,
            }
            for row in analysis.top_merchants[:10]
        ],
        "крупные_покупки": [
            {"описание": clean_merchant(t.description), "сумма": money(t.abs_amount),
             "дата": t.date.strftime("%d.%m.%Y")}
            for t in analysis.biggest[:5]
        ],
        "регулярные_платежи": [
            {
                "название": r.merchant,
                "средняя_сумма": money(r.average),
                "раз_за_период": r.count,
                "в_год": money(r.per_year),
                "категория": r.category,
            }
            for r in analysis.regulars
        ],
        "по_месяцам": [
            {
                "месяц": row.label,
                "сумма": money(row.amount),
                "операций": row.count,
                "главная_статья": row.top_category,
                "изменение_к_прошлому_месяцу_процент": (
                    round(row.delta, 1) if row.delta is not None else None
                ),
            }
            for row in analysis.months_detail
        ],
        "накопления_и_долги": {
            "отложено_на_накопительные_счета": money(analysis.saved_to_savings),
            "погашено_долга": money(analysis.debt_repaid),
            "долг_вырос_на": money(analysis.debt_increased),
            "одолжено_и_не_возвращено": money(analysis.lent_not_returned),
        },
    }
