"""Взаимозачёт переводов.

Перевод сам по себе не трата. Тратой является только непокрытый остаток,
и его смысл зависит от того, что за счёт на другом конце.

Переводы людям зачитываются полностью автоматически, без вопросов:

    дал −500, вернул +500  →  сальдо 0    →  расхода нет
    дал −500, вернул +300  →  сальдо −200 →  расход 200 ₽

Свои счета – каждый считается сам по себе, схлопывать их в общий котёл нельзя,
потому что смысл сальдо у разных счетов разный:

    накопительный:  ушло больше → отложено (не расход)
                    пришло больше → сняли из накоплений (не доход)
    кредитный:      ушло больше → погашение долга (это расход)
                    пришло больше → долг вырос (не доход, а заём у себя)
    обычный свой:   перекладывание из кармана в карман, нейтрально

У большинства пользователей загружена выписка только по одному счёту, и это
и есть весь их бюджет – спрашивать про каждый мелкий внутренний перевод
бессмысленно: раз выписка одна, значит, это один счёт, и мелочь можно
безопасно считать нейтральной. Вопрос задаётся только когда перевод на
неопознанный счёт – заметная доля оборота: тогда спрашиваем, чей это счёт
(«мой второй» – просим догрузить его выписку; «чужой» – и дальше это просто
перевод человеку, тоже без дополнительных вопросов).

Ограничение метода: зачёт возможен только внутри загруженного периода.
Если в долг дали в январе, а вернули в марте, месячная выписка увидит
только расход. Об этом честно пишется в интерфейсе.
"""

from __future__ import annotations

import re
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from decimal import Decimal

from .models import KIND_PERSON, KIND_SELF, Counterparty, Transaction

# Сальдо в пределах рубля считаем нулевым – это округления, а не трата.
TOLERANCE = Decimal("1.00")

# Перевод на неопознанный свой счёт считается заметным, если оборот по нему –
# не меньше этой доли общих расходов и не меньше абсолютного пола. Ниже порога
# вопрос не задаётся вообще: раз выписка одна, мелкие внутренние движения
# безопасно считать нейтральными и не дёргать пользователя.
SIGNIFICANT_FLOOR = Decimal("5000")
SIGNIFICANT_RATIO = Decimal("0.02")

# Типы своих счетов.
ACC_SAVINGS = "savings"   # накопительный: уход туда – сбережения
ACC_CREDIT = "credit"     # кредитный: уход туда – погашение долга
ACC_NEUTRAL = "neutral"   # другой свой счёт: просто перекладывание
ACC_UNKNOWN = "unknown"   # ещё не уточнён

ACCOUNT_TITLES = {
    ACC_SAVINGS: "накопительный",
    ACC_CREDIT: "кредитный",
    ACC_NEUTRAL: "обычный свой счёт",
    ACC_UNKNOWN: "назначение не указано",
}

# Ответ на вопрос «чей это счёт».
OWNER_SELF = "self"     # мой второй счёт – просим выписку
OWNER_OTHER = "other"   # счёт другого человека – дальше как обычный перевод

# Ручные пометки для переводов людям – используются программно (не из UI).
OVERRIDE_NET = "net"
OVERRIDE_EXPENSE = "expense"
OVERRIDE_IGNORE = "ignore"

_CONTRACT_KEY_RE = re.compile(r"^договор\s*(\d+)$")


def _extract_contract(key: str) -> str | None:
    """Номер договора из ключа контрагента, если это вообще похоже на счёт."""
    if m := _CONTRACT_KEY_RE.match(key):
        return m.group(1)
    return None


@dataclass
class NettingResult:
    counterparties: "OrderedDict[str, Counterparty]" = field(default_factory=OrderedDict)
    gross_expense: Decimal = Decimal(0)     # расходы как в выписке
    net_expense: Decimal = Decimal(0)       # расходы после взаимозачёта
    gross_income: Decimal = Decimal(0)
    net_income: Decimal = Decimal(0)        # поступления без возвратов своих же денег
    transfer_expense: Decimal = Decimal(0)  # сколько из переводов осталось расходом
    saved_to_savings: Decimal = Decimal(0)  # отложено на накопительные счета
    taken_from_savings: Decimal = Decimal(0)
    debt_repaid: Decimal = Decimal(0)       # погашено долга по кредиткам
    debt_increased: Decimal = Decimal(0)    # на столько вырос долг
    unclear_outgoing: Decimal = Decimal(0)  # ушло на счета с неуточнённым назначением
    purchases: list[Transaction] = field(default_factory=list)

    @property
    def saved_by_netting(self) -> Decimal:
        """Насколько взаимозачёт уменьшил видимый расход."""
        return self.gross_expense - self.net_expense

    def self_accounts(self) -> list[Counterparty]:
        return [c for c in self.counterparties.values() if c.kind == KIND_SELF]

    def people(self) -> list[Counterparty]:
        return [c for c in self.counterparties.values() if c.kind == KIND_PERSON]

    def accounts_to_classify(self) -> list[Counterparty]:
        """Свои счета с заметным оборотом – для выбора типа (вклад/кредит/другое)."""
        return [c for c in self.self_accounts() if c.significant and c.pending is None]

    def accounts_pending_choice(self) -> list[Counterparty]:
        """Неопознанные счета с заметным оборотом – нужно спросить, чьи они."""
        return [c for c in self.self_accounts() if c.pending == "choice"]

    def accounts_pending_upload(self) -> list[Counterparty]:
        """Пользователь сказал «это мой счёт» – ждём по нему выписку."""
        return [c for c in self.self_accounts() if c.pending == "upload"]

    def needs_clarification(self) -> list[Counterparty]:
        """Оставлено для CLI: то же, что accounts_pending_choice."""
        return self.accounts_pending_choice()


def _title_for(key: str, kind: str) -> str:
    if kind == KIND_SELF:
        if key == "Кубышка":
            return "Кубышка (накопительный счёт)"
        if key.startswith("договор"):
            return f"Счёт, {key}"
        if key == "свой счёт":
            return "Перевод себе"
        return key.capitalize()
    if key == "сбп-без-номера":
        return "Входящие переводы (СБП, отправитель не указан)"
    if key.isdigit() and len(key) == 10:
        return f"+7 {key[:3]} {key[3:6]}-{key[6:8]}-{key[8:]}"
    return key


def _default_account_type(key: str) -> str:
    """Что можно понять о счёте из его названия без вопросов к пользователю."""
    low = key.lower()
    if "кубышк" in low or "накопит" in low:
        return ACC_SAVINGS
    if "кредит" in low:
        return ACC_CREDIT
    return ACC_UNKNOWN


def compute(
    transactions: list[Transaction],
    overrides: dict[str, str] | None = None,
    account_types: dict[str, str] | None = None,
    merge_groups: dict[str, str] | None = None,
    account_owner: dict[str, str] | None = None,
    linked_contracts: set[str] | None = None,
) -> NettingResult:
    """Свести переводы по контрагентам и пересчитать расходы.

    overrides – пометки для переводов людям (net / expense / ignore); в обычном
        UI не задаются, взаимозачёт по людям всегда автоматический.
    account_types – типы своих счетов (savings / credit / neutral), заданные в UI,
        только для счетов с заметным оборотом.
    merge_groups – объединение ключей в один счёт (см. docstring раньше – на
        случай, когда банк называет один счёт по-разному в разных направлениях).
    account_owner – ответ на вопрос «чей это счёт» для неопознанных переводов
        (self – мой второй счёт, other – счёт другого человека).
    linked_contracts – номера договоров, по которым уже загружена своя выписка:
        такие счета не переспрашиваются binary-вопросом, для них сразу можно
        выбирать тип.
    """
    overrides = overrides or {}
    account_types = account_types or {}
    merge_groups = merge_groups or {}
    account_owner = account_owner or {}
    linked_contracts = linked_contracts or set()
    result = NettingResult()

    for tx in transactions:
        if tx.amount < 0:
            result.gross_expense += tx.abs_amount
        else:
            result.gross_income += tx.amount

        if tx.kind in (KIND_SELF, KIND_PERSON) and tx.counterparty:
            key = merge_groups.get(tx.counterparty, tx.counterparty)
            party = result.counterparties.get(key)
            if party is None:
                party = Counterparty(
                    key=key,
                    title=_title_for(key, tx.kind),
                    kind=tx.kind,
                )
                result.counterparties[key] = party
            if key != tx.counterparty and tx.counterparty not in party.merged_from:
                party.merged_from.append(tx.counterparty)
            if tx.amount < 0:
                party.outgoing += tx.abs_amount
            else:
                party.incoming += tx.amount
            party.count += 1
        else:
            result.purchases.append(tx)

    non_transfer_expense = sum(
        (t.abs_amount for t in result.purchases if t.amount < 0), Decimal(0)
    )
    non_transfer_income = sum(
        (t.amount for t in result.purchases if t.amount > 0), Decimal(0)
    )

    # Порог заметности считается от общих расходов – раньше он не может быть известен.
    threshold = max(SIGNIFICANT_FLOOR, result.gross_expense * SIGNIFICANT_RATIO)

    transfer_expense = Decimal(0)
    transfer_income = Decimal(0)

    for party in result.counterparties.values():
        party.override = overrides.get(party.key)
        if party.override == OVERRIDE_IGNORE:
            continue

        # Пользователь сказал «это счёт другого человека» – с этого момента
        # переводы туда считаются как обычный перевод человеку, без вопросов.
        if party.kind == KIND_SELF and account_owner.get(party.key) == OWNER_OTHER:
            party.kind = KIND_PERSON

        netto = party.netto

        if party.kind == KIND_PERSON:
            if party.override == OVERRIDE_EXPENSE:
                transfer_expense += party.outgoing
            elif netto < -TOLERANCE:
                # Дали больше, чем вернули – разница действительно потрачена.
                transfer_expense += -netto
            elif netto > TOLERANCE:
                transfer_income += netto
            continue

        # --- дальше только свои счета ---
        contract = _extract_contract(party.key)
        party.contract = contract
        is_linked = contract is not None and contract in linked_contracts
        turnover = max(party.outgoing, party.incoming)
        party.significant = turnover >= threshold

        auto_type = _default_account_type(party.key)

        if contract and party.significant and not is_linked and auto_type == ACC_UNKNOWN:
            owner = account_owner.get(party.key)
            if owner == OWNER_SELF:
                party.pending = "upload"
                # Пока выписка по этому счёту не загружена, его сальдо не в счёт
                # расходов – иначе цифра будет расти и падать до полной картины.
                continue
            party.pending = "choice"
            continue

        chosen_type = account_types.get(party.key, auto_type)
        party.account_type = chosen_type

        if chosen_type == ACC_SAVINGS:
            if netto < -TOLERANCE:
                result.saved_to_savings += -netto      # отложено, не потрачено
            elif netto > TOLERANCE:
                result.taken_from_savings += netto     # сняли своё, не заработали
        elif chosen_type == ACC_CREDIT:
            if netto < -TOLERANCE:
                result.debt_repaid += -netto
                transfer_expense += -netto             # погашение долга – расход
            elif netto > TOLERANCE:
                result.debt_increased += netto         # заняли у банка, не доход
        else:
            # Обычный свой счёт или мелкий неопознанный: перекладывание, нейтрально.
            if netto < -TOLERANCE and chosen_type == ACC_UNKNOWN:
                result.unclear_outgoing += -netto

    result.transfer_expense = transfer_expense
    result.net_expense = non_transfer_expense + transfer_expense
    result.net_income = non_transfer_income + transfer_income
    return result


def _cli() -> None:
    if len(sys.argv) < 2:
        print("использование: python -m app.netting <файл.pdf>")
        raise SystemExit(1)

    from .categorizer import categorize_all
    from .parser import parse_statement

    txs, report = parse_statement(open(sys.argv[1], "rb").read())
    txs = categorize_all(txs)
    res = compute(txs)

    print(f"период: {report.period_start:%d.%m.%Y} – {report.period_end:%d.%m.%Y}")
    print()
    print(f"{'контрагент':<44}{'тип':<22}{'пришло':>13}{'ушло':>13}{'сальдо':>13}")
    for party in sorted(res.counterparties.values(), key=lambda p: -max(p.outgoing, p.incoming)):
        kind = ACCOUNT_TITLES.get(party.account_type, "человек") if party.kind == KIND_SELF else "человек"
        print(
            f"{party.title[:42]:<44}{kind:<22}{party.incoming:>13,.2f}"
            f"{party.outgoing:>13,.2f}{party.netto:>13,.2f}"
        )
    print()
    print(f"валовый расход:        {res.gross_expense:>13,.2f} ₽  (как в выписке)")
    print(f"чистый расход:         {res.net_expense:>13,.2f} ₽  (после взаимозачёта)")
    print(f"взаимозачёт убрал:     {res.saved_by_netting:>13,.2f} ₽")
    print()
    print(f"отложено в накопления: {res.saved_to_savings:>13,.2f} ₽")
    print(f"снято из накоплений:   {res.taken_from_savings:>13,.2f} ₽")
    print(f"погашено долга:        {res.debt_repaid:>13,.2f} ₽")
    print(f"долг вырос на:         {res.debt_increased:>13,.2f} ₽")
    print(f"ушло на счета без типа:{res.unclear_outgoing:>13,.2f} ₽")
    if res.accounts_pending_choice():
        print()
        print("нужно спросить, чей это счёт:")
        for c in res.accounts_pending_choice():
            print(f"  • {c.title}: сальдо {c.netto:,.2f} ₽")


if __name__ == "__main__":
    _cli()
