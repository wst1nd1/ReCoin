"""Разбор PDF-выписки в список операций.

Основной формат – «Справка о движении средств» Т-Банка, где одна операция
занимает несколько строк текста:

    31.08.2026 01.09.2026 -810.00 ₽ -810.00 ₽ Оплата в 9781
    22:37 03:18 YANDEX*5411*EDARIT
    Moskva RUS

Первая строка операции всегда начинается с даты – по этому признаку блоки
и разделяются. Для других банков есть запасной построчный разбор.
"""

from __future__ import annotations

import io
import re
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pdfplumber

from .models import ParseReport, Transaction

# В суммах встречаются обычный пробел, неразрывный (U+00A0) и узкий (U+202F).
_SPACES = "    "

# Первая строка операции: две даты, две суммы, начало описания, номер карты.
_ROW_RE = re.compile(
    r"^(?P<date>\d{2}\.\d{2}\.\d{4})\s+"
    r"(?P<posted>\d{2}\.\d{2}\.\d{4})\s+"
    r"(?P<amount>[+-][\d" + _SPACES + r"]*[.,]\d{2})\s*[₽$€]?\s+"
    r"(?P<amount_card>[+-][\d" + _SPACES + r"]*[.,]\d{2})\s*[₽$€]?\s*"
    r"(?P<rest>.*)$"
)

# Вторая строка операции начинается с двух отметок времени.
_TIME_RE = re.compile(r"^(?P<t1>\d{2}:\d{2})\s+(?P<t2>\d{2}:\d{2})\s*(?P<rest>.*)$")

# Хвост первой строки: описание и номер карты («9781» либо прочерк).
# Прочерк в самой выписке набран длинным тире, поэтому в шаблоне допускаются
# оба начертания – это внешние данные, а не наш текст.
_CARD_TAIL_RE = re.compile(r"^(?P<desc>.*?)\s*(?P<card>\d{4}|[–—])$")

# Строки-шум: колонтитулы, реквизиты банка, номера страниц.
_NOISE_RE = re.compile(
    r"АО\s*«ТБанк»|БИК\s|ИНН\s|КПП\s|лицензи|^\d{1,3}$|^Дата и время|^операции\s|"
    r"^С уважением|Руководитель Управления|ТЕЛ\.:|РОССИЯ,|АКЦИОНЕРНОЕ ОБЩЕСТВО|"
    r"Справка о движении|Исх\. №|Адрес места жительства|^О продукте|"
    r"Дата заключения договора|Номер договора|Номер лицевого счета|Движение средств за период",
    re.IGNORECASE,
)

_PERIOD_RE = re.compile(r"за период с (\d{2}\.\d{2}\.\d{4}) по (\d{2}\.\d{2}\.\d{4})")
_TOTAL_INCOME_RE = re.compile(r"Пополнени[яй]:\s*([\d" + _SPACES + r"]*[.,]\d{2})")
_TOTAL_EXPENSE_RE = re.compile(r"Расход[ыа]:\s*([\d" + _SPACES + r"]*[.,]\d{2})")
_MCC_RE = re.compile(r"\*(\d{4})\*")
_CONTRACT_RE = re.compile(r"Номер договора:\s*(\d+)")
_ACCOUNT_RE = re.compile(r"Номер лицевого счета:\s*(\d+)")
_HOLDER_RE = re.compile(r"^([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)$")


def parse_amount(raw: str) -> Decimal:
    """«-1 000.00» / «+218 517,79» → Decimal."""
    cleaned = raw.strip()
    for ch in _SPACES:
        cleaned = cleaned.replace(ch, "")
    cleaned = cleaned.replace("₽", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"не сумма: {raw!r}") from exc


def _extract_lines(data: bytes) -> list[str]:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return [ln.strip() for ln in "\n".join(pages).split("\n") if ln.strip()]


def _finish(block: list[str], report: ParseReport) -> Transaction | None:
    """Собрать операцию из накопленных строк блока."""
    head = _ROW_RE.match(block[0])
    if not head:
        return None

    try:
        amount = parse_amount(head.group("amount_card") or head.group("amount"))
    except ValueError:
        report.skipped += 1
        return None

    # Описание: хвост первой строки без номера карты + продолжение со следующих.
    rest = head.group("rest").strip()
    card = None
    tail = _CARD_TAIL_RE.match(rest)
    if tail:
        rest = tail.group("desc").strip()
        card = tail.group("card")
        if card in ("–", "—"):
            card = None

    parts = [rest] if rest else []
    time_str = None
    for line in block[1:]:
        tm = _TIME_RE.match(line)
        if tm:
            time_str = tm.group("t1")
            extra = tm.group("rest").strip()
        else:
            extra = line.strip()
        # Номер карты стоит только в первой строке, поэтому продолжения
        # берём как есть – иначе у «договор 8070561062» отрежется хвост.
        if extra:
            parts.append(extra)

    description = " ".join(parts).strip()

    date_str = head.group("date")
    stamp = f"{date_str} {time_str}" if time_str else date_str
    fmt = "%d.%m.%Y %H:%M" if time_str else "%d.%m.%Y"
    try:
        date = datetime.strptime(stamp, fmt)
    except ValueError:
        report.skipped += 1
        return None

    posted = None
    try:
        posted = datetime.strptime(head.group("posted"), "%d.%m.%Y")
    except ValueError:
        pass

    mcc_match = _MCC_RE.search(description)

    return Transaction(
        date=date,
        amount=amount,
        description=description,
        posted=posted,
        card=card,
        mcc=mcc_match.group(1) if mcc_match else None,
        raw_lines=list(block),
    )


def parse_statement(data: bytes) -> tuple[list[Transaction], ParseReport]:
    """PDF-выписка → операции и отчёт о качестве разбора."""
    lines = _extract_lines(data)
    report = ParseReport()

    joined = "\n".join(lines)
    if "ТБАНК" in joined.upper() or "TinkoffSans" in joined:
        report.bank = "Т-Банк"

    if m := _PERIOD_RE.search(joined):
        report.period_start = datetime.strptime(m.group(1), "%d.%m.%Y")
        report.period_end = datetime.strptime(m.group(2), "%d.%m.%Y")
    if m := _TOTAL_INCOME_RE.search(joined):
        report.stated_income = parse_amount(m.group(1))
    if m := _TOTAL_EXPENSE_RE.search(joined):
        report.stated_expense = parse_amount(m.group(1))
    # Номер договора нужен, чтобы связать несколько выписок одного человека:
    # «перевод на договор N» из одной выписки – это и есть другой его счёт.
    if m := _CONTRACT_RE.search(joined):
        report.contract = m.group(1)
    if m := _ACCOUNT_RE.search(joined):
        report.account = m.group(1)

    transactions: list[Transaction] = []
    block: list[str] = []

    for line in lines:
        if _NOISE_RE.search(line):
            # Колонтитул может разрывать многострочную операцию – просто пропускаем.
            continue
        if report.account_holder is None and (m := _HOLDER_RE.match(line)):
            report.account_holder = m.group(1)
            continue

        if _ROW_RE.match(line):
            if block:
                if tx := _finish(block, report):
                    transactions.append(tx)
            block = [line]
        elif block:
            block.append(line)

    if block:
        if tx := _finish(block, report):
            transactions.append(tx)

    report.parsed = len(transactions)

    if not transactions:
        report.warnings.append(
            "Не удалось распознать ни одной операции. "
            "Возможно, это выписка другого банка или PDF со сканами вместо текста."
        )
    else:
        income = sum((t.amount for t in transactions if t.amount > 0), Decimal(0))
        expense = sum((t.abs_amount for t in transactions if t.amount < 0), Decimal(0))
        if not report.matches_stated(income, expense):
            report.warnings.append(
                f"Наши итоги ({expense:.2f} ₽ расходов) расходятся с указанными в выписке "
                f"({report.stated_expense:.2f} ₽). Часть операций могла не распознаться."
            )

    return transactions, report


def _cli() -> None:
    if len(sys.argv) < 2:
        print("использование: python -m app.parser <файл.pdf>")
        raise SystemExit(1)

    data = open(sys.argv[1], "rb").read()
    txs, report = parse_statement(data)

    income = sum((t.amount for t in txs if t.amount > 0), Decimal(0))
    expense = sum((t.abs_amount for t in txs if t.amount < 0), Decimal(0))

    print(f"банк:      {report.bank}")
    print(f"владелец:  {report.account_holder}")
    if report.period_start:
        print(f"период:    {report.period_start:%d.%m.%Y} – {report.period_end:%d.%m.%Y}")
    print(f"операций:  {report.parsed} (пропущено {report.skipped})")
    print()
    print(f"пополнения: {income:>12,.2f} ₽   в выписке: {report.stated_income}")
    print(f"расходы:    {expense:>12,.2f} ₽   в выписке: {report.stated_expense}")
    print(f"сходится:   {report.matches_stated(income, expense)}")
    for w in report.warnings:
        print(f"! {w}")
    print()
    print("первые 15 операций:")
    for t in txs[:15]:
        print(f"  {t.date:%d.%m %H:%M}  {t.amount:>12,.2f}  {t.description[:60]}")


if __name__ == "__main__":
    _cli()
