"""Сведение нескольких выписок одного пользователя.

Выписка по одному счёту показывает только его операции. Траты, сделанные
напрямую с кредитной карты, в выписке дебетового счёта не видны – поэтому
долг по карте из неё посчитать нельзя. Как только пользователь загружает
выписки по нескольким своим счетам, картина закрывается:

* номер договора есть в шапке каждой выписки, поэтому «перевод на договор N»
  автоматически опознаётся как перевод на другой загруженный счёт – без
  вопросов пользователю и без привязки к конкретным номерам;
* один и тот же перевод виден дважды (списание в одной выписке, зачисление
  в другой) – вторую половину нужно убрать, иначе обороты задвоятся.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from .models import KIND_SELF, ParseReport, Transaction

# Насколько разъезжаются даты у двух половин одного перевода.
PAIR_WINDOW = timedelta(days=3)


@dataclass
class Statement:
    """Одна загруженная выписка."""

    report: ParseReport
    transactions: list[Transaction]

    @property
    def contract(self) -> str | None:
        return self.report.contract

    @property
    def label(self) -> str:
        if self.report.contract:
            return f"счёт по договору {self.report.contract}"
        return self.report.source or "выписка"


@dataclass
class Portfolio:
    """Все выписки пользователя вместе."""

    statements: list[Statement] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    internal_pairs: int = 0                 # сколько встречных проводок схлопнулось
    internal_volume: Decimal = Decimal(0)   # на какую сумму
    notes: list[str] = field(default_factory=list)

    @property
    def contracts(self) -> set[str]:
        return {s.contract for s in self.statements if s.contract}

    @property
    def period(self) -> tuple[object, object]:
        starts = [s.report.period_start for s in self.statements if s.report.period_start]
        ends = [s.report.period_end for s in self.statements if s.report.period_end]
        return (min(starts) if starts else None, max(ends) if ends else None)


def _contract_in(description: str, contracts: set[str]) -> str | None:
    """Упомянут ли в описании номер одного из загруженных счетов."""
    for contract in contracts:
        if contract and contract in description:
            return contract
    return None


def build(statements: list[Statement]) -> Portfolio:
    """Свести выписки в один набор операций."""
    portfolio = Portfolio(statements=list(statements))
    contracts = portfolio.contracts

    # Помечаем операции: из какой выписки пришли и на какой свой счёт ссылаются.
    for statement in statements:
        own = statement.contract
        for tx in statement.transactions:
            tx.source_contract = own
            if tx.kind == KIND_SELF:
                if hit := _contract_in(tx.description, contracts - {own} if own else contracts):
                    # Перевод на другой загруженный счёт – связь известна точно.
                    tx.counterparty = f"договор {hit}"
                    tx.linked_contract = hit

    merged: list[Transaction] = []
    # Кандидаты на спаривание – все переводы между своими счетами. По номеру
    # договора связать удаётся не всегда: обратная половина часто приходит
    # безымянным «Переводом себе». Зато у пары всегда зеркальная сумма,
    # близкая дата и разные выписки – этого достаточно.
    pending: list[Transaction] = []

    for statement in statements:
        for tx in statement.transactions:
            if tx.kind == KIND_SELF and tx.source_contract:
                pending.append(tx)
            else:
                merged.append(tx)

    pending.sort(key=lambda t: t.date)
    used: set[int] = set()

    for i, tx in enumerate(pending):
        if i in used:
            continue
        partner_index = None
        for j in range(i + 1, len(pending)):
            if j in used:
                continue
            other = pending[j]
            if other.date - tx.date > PAIR_WINDOW:
                break  # дальше только более поздние – пары уже не будет
            if other.amount != -tx.amount:
                continue
            if other.source_contract == tx.source_contract:
                continue  # обе половины не могут быть из одной выписки
            # Если номер счёта в описании всё же разобран, он должен совпасть.
            if tx.linked_contract and tx.linked_contract != other.source_contract:
                continue
            if other.linked_contract and other.linked_contract != tx.source_contract:
                continue
            partner_index = j
            break

        if partner_index is None:
            merged.append(tx)
            continue

        used.add(i)
        used.add(partner_index)
        portfolio.internal_pairs += 1
        portfolio.internal_volume += tx.abs_amount
        # Обе половины – перекладывание внутри своих счетов. В расходах им
        # места нет: деньги не покинули пользователя.

    portfolio.transactions = sorted(merged, key=lambda t: t.date, reverse=True)

    if len(statements) > 1 and portfolio.internal_pairs:
        portfolio.notes.append(
            f"Найдено {portfolio.internal_pairs} переводов между вашими счетами "
            f"на {portfolio.internal_volume:,.0f} ₽ – они видны в обеих выписках "
            f"и в расходах не учитываются."
        )
    if len(statements) == 1:
        portfolio.notes.append(
            "Загружена выписка по одному счёту. Покупки, оплаченные напрямую "
            "с других карт, сюда не попадают – добавьте их выписки для полной картины."
        )

    return portfolio
