"""Сведение нескольких выписок одного пользователя."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app import portfolio
from app.models import KIND_PURCHASE, KIND_SELF, ParseReport, Transaction


def tx(amount: str, desc: str, kind: str = KIND_PURCHASE, day: int = 5) -> Transaction:
    return Transaction(
        date=datetime(2026, 8, day, 12, 0),
        amount=Decimal(amount),
        description=desc,
        kind=kind,
    )


def statement(contract: str, transactions: list[Transaction]) -> portfolio.Statement:
    report = ParseReport(contract=contract, parsed=len(transactions))
    return portfolio.Statement(report=report, transactions=transactions)


def test_встречные_проводки_не_задваиваются():
    """Перевод между своими счетами виден в обеих выписках – считаем один раз."""
    debit = statement("111", [tx("-5000", "Внутренний перевод на договор 222", KIND_SELF)])
    credit = statement("222", [tx("+5000", "Перевод себе", KIND_SELF)])

    result = portfolio.build([debit, credit])

    assert result.internal_pairs == 1
    assert result.internal_volume == Decimal(5000)
    # Обе половины исключены: деньги остались у пользователя.
    assert result.transactions == []


def test_счета_связываются_по_номеру_договора_без_подсказок():
    """Номер договора берётся из шапки выписки, руками ничего указывать не нужно."""
    debit = statement("111", [tx("-5000", "Внутренний перевод на договор 222", KIND_SELF)])
    credit = statement("222", [tx("+5000", "Перевод себе", KIND_SELF)])

    portfolio.build([debit, credit])

    assert debit.transactions[0].linked_contract == "222"
    assert debit.transactions[0].counterparty == "договор 222"


def test_покупки_с_кредитки_видны_только_во_второй_выписке():
    """Ради этого и нужна загрузка нескольких выписок."""
    debit = statement("111", [tx("-5000", "Внутренний перевод на договор 222", KIND_SELF)])
    credit = statement(
        "222",
        [
            tx("+5000", "Перевод себе", KIND_SELF),
            tx("-3000", "Оплата в DNS"),
        ],
    )

    result = portfolio.build([debit, credit])

    descriptions = [t.description for t in result.transactions]
    assert descriptions == ["Оплата в DNS"]


def test_перевод_без_второй_выписки_остаётся_как_есть():
    """Если счёт-получатель не загружен, спаривать не с чем."""
    debit = statement("111", [tx("-5000", "Внутренний перевод на договор 999", KIND_SELF)])

    result = portfolio.build([debit])

    assert result.internal_pairs == 0
    assert len(result.transactions) == 1
    assert result.notes  # предупреждение о неполной картине


def test_разные_даты_половин_одного_перевода():
    """Списание и зачисление могут разъехаться на день-два."""
    debit = statement("111", [tx("-5000", "Внутренний перевод на договор 222", KIND_SELF, day=5)])
    credit = statement("222", [tx("+5000", "Перевод себе", KIND_SELF, day=7)])

    result = portfolio.build([debit, credit])

    assert result.internal_pairs == 1


def test_похожие_но_разные_переводы_не_склеиваются():
    """Две разные суммы не должны спариться между собой."""
    debit = statement(
        "111",
        [
            tx("-5000", "Внутренний перевод на договор 222", KIND_SELF, day=5),
            tx("-7000", "Внутренний перевод на договор 222", KIND_SELF, day=6),
        ],
    )
    credit = statement("222", [tx("+5000", "Перевод себе", KIND_SELF, day=5)])

    result = portfolio.build([debit, credit])

    assert result.internal_pairs == 1
    assert len(result.transactions) == 1
    assert result.transactions[0].amount == Decimal(-7000)
