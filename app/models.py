"""Модели данных ReCoin.

Деньги считаются в Decimal – float для финансов не годится.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

# Виды операций. Влияют на то, попадёт ли операция во взаимозачёт.
KIND_PURCHASE = "purchase"           # обычная трата у мерчанта
KIND_SELF = "self"                   # перевод между своими счетами
KIND_PERSON = "person"               # перевод физлицу / от физлица
KIND_CASHBACK = "cashback"           # кэшбэк, проценты, бонусы
KIND_INCOME = "income"               # зарплата и прочие поступления
KIND_CASH = "cash"                   # снятие наличных


@dataclass
class Transaction:
    """Одна операция по счёту."""

    date: datetime
    amount: Decimal                  # со знаком: минус – расход, плюс – приход
    description: str
    posted: datetime | None = None   # дата списания
    card: str | None = None
    mcc: str | None = None
    category: str = ""
    kind: str = KIND_PURCHASE
    counterparty: str | None = None  # ключ для взаимозачёта (телефон, «Кубышка», номер договора)
    raw_lines: list[str] = field(default_factory=list)
    source_contract: str | None = None   # договор выписки, из которой операция
    linked_contract: str | None = None   # договор другого своего счёта, если это перевод между ними

    @property
    def is_expense(self) -> bool:
        return self.amount < 0

    @property
    def abs_amount(self) -> Decimal:
        return abs(self.amount)


@dataclass
class ParseReport:
    """Насколько хорошо разобрался файл – показывается пользователю."""

    parsed: int = 0
    skipped: int = 0
    period_start: datetime | None = None
    period_end: datetime | None = None
    account_holder: str | None = None
    stated_income: Decimal | None = None   # «Пополнения» из подвала выписки
    stated_expense: Decimal | None = None  # «Расходы» из подвала выписки
    bank: str = "неизвестен"
    contract: str | None = None            # номер договора этой выписки
    account: str | None = None             # номер лицевого счёта
    source: str = ""                       # имя загруженного файла
    warnings: list[str] = field(default_factory=list)

    def matches_stated(self, income: Decimal, expense: Decimal, tol: Decimal = Decimal("0.01")) -> bool:
        """Сошлись ли наши суммы с теми, что банк напечатал в выписке."""
        if self.stated_income is None or self.stated_expense is None:
            return True
        return abs(income - self.stated_income) <= tol and abs(expense - self.stated_expense) <= tol


@dataclass
class Counterparty:
    """Контрагент для взаимозачёта: свой счёт или человек."""

    key: str
    title: str
    kind: str                        # KIND_SELF | KIND_PERSON
    incoming: Decimal = Decimal(0)   # пришло от него
    outgoing: Decimal = Decimal(0)   # ушло ему
    count: int = 0
    override: str | None = None      # ручная пометка из UI: net | expense | ignore
    account_type: str = "unknown"    # для своих счетов: savings | credit | neutral | unknown
    merged_from: list[str] = field(default_factory=list)  # ключи, слитые в этот счёт
    contract: str | None = None      # номер договора, если он виден в описании перевода
    significant: bool = False        # оборот заметный на фоне общих трат
    pending: str | None = None       # None | "choice" (чей счёт?) | "upload" (ждём выписку)

    @property
    def netto(self) -> Decimal:
        """Сальдо. Отрицательное – деньги ушли и не вернулись."""
        return self.incoming - self.outgoing

    @property
    def real_expense(self) -> Decimal:
        """Сколько из этих переводов действительно потрачено."""
        return -self.netto if self.netto < 0 else Decimal(0)
