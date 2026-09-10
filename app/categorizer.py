"""Определение категории и вида операции.

Порядок решения:
  1. вид операции (перевод себе, перевод человеку, кэшбэк, наличные…);
  2. MCC, если он есть в описании;
  3. словарь мерчантов;
  4. «Прочее» – такие описания потом добирает модель.
"""

from __future__ import annotations

import re

from . import mcc as M
from .models import (
    KIND_CASH,
    KIND_CASHBACK,
    KIND_INCOME,
    KIND_PERSON,
    KIND_PURCHASE,
    KIND_SELF,
    Transaction,
)

# Ключевое слово → категория. Регистр не важен, ищется вхождение подстроки.
_MERCHANTS: list[tuple[str, str]] = [
    # Продукты
    ("magnit", M.FOOD),
    ("pyaterochka", M.FOOD),
    ("perekrestok", M.FOOD),
    ("lenta", M.FOOD),
    ("dixy", M.FOOD),
    ("okey", M.FOOD),
    ("auchan", M.FOOD),
    ("vkusvill", M.FOOD),
    ("krasnoe&beloe", M.FOOD),
    ("krasnoe", M.FOOD),
    ("bristol", M.FOOD),
    ("lavka", M.FOOD),
    ("samokat", M.FOOD),
    ("edarit", M.FOOD),
    ("sladkoezhka", M.FOOD),
    ("sladeniev", M.FOOD),
    ("pitevoj", M.FOOD),
    ("istochnik", M.FOOD),
    ("пятероч", M.FOOD),
    ("магнит", M.FOOD),
    ("перекрёст", M.FOOD),
    ("перекрест", M.FOOD),
    ("вкусвилл", M.FOOD),
    ("самокат", M.FOOD),
    # Кафе и доставка готовой еды
    ("yandex*5814", M.CAFE),
    ("stolovaya", M.CAFE),
    ("pizza", M.CAFE),
    ("cafe", M.CAFE),
    ("coffee", M.CAFE),
    ("kofe", M.CAFE),
    ("cheburek", M.CAFE),
    ("tom yam", M.CAFE),
    ("shaurma", M.CAFE),
    ("burger", M.CAFE),
    ("kfc", M.CAFE),
    ("vkusno", M.CAFE),
    ("столов", M.CAFE),
    ("кафе", M.CAFE),
    ("рестор", M.CAFE),
    ("delivery", M.CAFE),
    ("delivery club", M.CAFE),
    # Транспорт
    ("proezd", M.TRANSPORT),
    ("proezda", M.TRANSPORT),
    ("rzd", M.TRANSPORT),
    ("railway", M.TRANSPORT),
    ("poezd", M.TRANSPORT),
    ("fpk", M.TRANSPORT),
    ("aeroflot", M.TRANSPORT),
    ("pobeda", M.TRANSPORT),
    ("s7", M.TRANSPORT),
    ("uber", M.TRANSPORT),
    ("citymobil", M.TRANSPORT),
    ("ehkspress", M.TRANSPORT),
    ("express-pr", M.TRANSPORT),
    ("metro", M.TRANSPORT),
    ("troika", M.TRANSPORT),
    ("prigorod", M.TRANSPORT),
    ("проезд", M.TRANSPORT),
    ("метро", M.TRANSPORT),
    ("ржд", M.TRANSPORT),
    ("такси", M.TRANSPORT),
    ("заправк", M.TRANSPORT),
    ("лукойл", M.TRANSPORT),
    ("газпромнефть", M.TRANSPORT),
    ("роснефть", M.TRANSPORT),
    # Развлечения
    ("kinokassa", M.FUN),
    ("kino", M.FUN),
    ("cinema", M.FUN),
    ("gameplus", M.FUN),
    ("game", M.FUN),
    ("steam", M.FUN),
    ("amfiteatr", M.FUN),
    ("teatr", M.FUN),
    ("bilet", M.FUN),
    ("кино", M.FUN),
    ("театр", M.FUN),
    ("билет", M.FUN),
    ("бар ", M.FUN),
    # Ставки. ЦУПИС – платёжный центр букмекеров, через него идут все переводы
    # в легальные конторы, поэтому в выписке он выглядит нейтрально.
    ("betboom", M.BETS),
    ("cupis", M.BETS),
    ("fonbet", M.BETS),
    ("winline", M.BETS),
    ("1xbet", M.BETS),
    ("marathonbet", M.BETS),
    ("liga stavok", M.BETS),
    ("ligastavok", M.BETS),
    ("pari.ru", M.BETS),
    ("betcity", M.BETS),
    ("olimpbet", M.BETS),
    ("ставк", M.BETS),
    ("букмекер", M.BETS),
    # Спортзалы и фитнес
    ("ddx", M.GYM),
    ("fitness", M.GYM),
    ("fitnes", M.GYM),
    ("world class", M.GYM),
    ("worldclass", M.GYM),
    ("spirit fitness", M.GYM),
    ("alex fitness", M.GYM),
    ("zebra", M.GYM),
    ("фитнес", M.GYM),
    ("спортзал", M.GYM),
    ("тренаж", M.GYM),
    ("бассейн", M.GYM),
    # Подписки и цифровые сервисы
    ("yandex*5815", M.SUBS),
    ("yandex plus", M.SUBS),
    ("сервисы яндекса", M.SUBS),
    ("яндекс плюс", M.SUBS),
    ("proxytg", M.SUBS),
    ("vpn", M.SUBS),
    ("spotify", M.SUBS),
    ("netflix", M.SUBS),
    ("apple.com", M.SUBS),
    ("google", M.SUBS),
    ("подписка", M.SUBS),
    ("kion", M.SUBS),
    ("okko", M.SUBS),
    ("ivi", M.SUBS),
    # Связь
    ("mts", M.CONNECT),
    ("megafon", M.CONNECT),
    ("beeline", M.CONNECT),
    ("tele2", M.CONNECT),
    ("rostelecom", M.CONNECT),
    ("мтс", M.CONNECT),
    ("мегафон", M.CONNECT),
    ("билайн", M.CONNECT),
    ("ростелеком", M.CONNECT),
    ("связь", M.CONNECT),
    ("ehr-telekom", M.CONNECT),
    ("эр-телеком", M.CONNECT),
    ("dom.ru", M.CONNECT),
    # Здоровье
    ("apteka", M.HEALTH),
    ("pharm", M.HEALTH),
    ("rigla", M.HEALTH),
    ("stomat", M.HEALTH),
    ("klinika", M.HEALTH),
    ("medic", M.HEALTH),
    ("invitro", M.HEALTH),
    ("gemotest", M.HEALTH),
    ("аптек", M.HEALTH),
    ("клиник", M.HEALTH),
    ("стомат", M.HEALTH),
    ("больниц", M.HEALTH),
    ("медиц", M.HEALTH),
    # Одежда и красота
    ("wildberries", M.CLOTHES),
    ("lamoda", M.CLOTHES),
    ("zara", M.CLOTHES),
    ("hm.com", M.CLOTHES),
    ("uniqlo", M.CLOTHES),
    ("sportmaster", M.CLOTHES),
    ("letual", M.CLOTHES),
    ("rive gauche", M.CLOTHES),
    ("barber", M.CLOTHES),
    ("salon", M.CLOTHES),
    ("парикмах", M.CLOTHES),
    ("салон", M.CLOTHES),
    # Жильё и ЖКУ
    ("zhku", M.HOUSING),
    ("gku", M.HOUSING),
    ("energosbyt", M.HOUSING),
    ("vodokanal", M.HOUSING),
    ("teploset", M.HOUSING),
    ("жку", M.HOUSING),
    ("коммунал", M.HOUSING),
    ("квартплат", M.HOUSING),
    ("аренда", M.HOUSING),
    ("энергосбыт", M.HOUSING),
    # Образование
    ("skillbox", M.EDU),
    ("netology", M.EDU),
    ("coursera", M.EDU),
    ("uchebn", M.EDU),
    ("школ", M.EDU),
    ("курс", M.EDU),
    ("универс", M.EDU),
    # Услуги
    ("sdek", M.SERVICES),
    ("cdek", M.SERVICES),
    ("сдэк", M.SERVICES),
    ("pochta", M.SERVICES),
    ("почта", M.SERVICES),
    ("pedant", M.SERVICES),
    ("remont", M.SERVICES),
    ("ремонт", M.SERVICES),
    ("himchistka", M.SERVICES),
    ("оплата услуг", M.SERVICES),
    ("nalog", M.SERVICES),
    ("налог", M.SERVICES),
    ("gosuslugi", M.SERVICES),
    ("госуслуг", M.SERVICES),
    # Маркетплейсы – товары для дома и всякое разное
    ("ozon", M.OTHER),
    ("aliexpress", M.OTHER),
    ("yandex market", M.OTHER),
    ("dns", M.OTHER),
    ("mvideo", M.OTHER),
    ("eldorado", M.OTHER),
    ("leroy", M.OTHER),
    ("fix price", M.OTHER),
]

# Признаки переводов между своими счетами.
_SELF_PATTERNS = [
    "кубышк",
    "перевод себе",
    "перевод средств из",
    "внутренний перевод",
    "перевод с договора",
    "между своими счетами",
    "накопительный счёт",
    "накопительный счет",
    "на кредитную карту",
    "со счета кредитной",
    "со счёта кредитной",
    "пополнение кредитн",
]

# Признаки переводов физлицам.
_PERSON_PATTERNS = [
    "внешний перевод",
    "перевод по номеру телефона",
    "система быстрых платежей",
    "сбп",
    "перевод физическому",
    "перевод клиенту",
]

_CASHBACK_PATTERNS = ["кэшбэк", "кешбэк", "cashback", "бонус", "проценты на остаток", "процент на остаток"]
_INCOME_PATTERNS = ["заработная плата", "зарплат", "аванс", "стипенди", "пенси", "возврат средств", "депозит"]
_CASH_PATTERNS = ["выдача наличных", "снятие наличных", "atm", "банкомат"]

_PHONE_RE = re.compile(r"\+?7?[\s(-]*(\d{3})[\s)-]*(\d{3})[\s-]*(\d{2})[\s-]*(\d{2})")
_CONTRACT_RE = re.compile(r"договор[аеу]?\s*(\d{6,})")

# Мусор в описании, мешающий читать название мерчанта.
# Правила по образцу названия – для сетей, у которых в выписке не имя, а код точки.
_PATTERN_RULES: list[tuple[re.Pattern[str], str]] = [
    # «Чижик» платёжная система показывает как CH + код региона + номер магазина:
    # CH61085 – Ростовская область, CH77xxx – Москва и так далее.
    (re.compile(r"\bch\d{5}\b", re.IGNORECASE), M.FOOD),
    # Аналогичная схема у «Пятёрочки» в части терминалов.
    (re.compile(r"\baia\*5ka\b", re.IGNORECASE), M.FOOD),
]

_CITY_TAIL_RE = re.compile(
    r"\s+(Moskva|Moscow|Rostov-na-\s*Don|Rostov-na-|Don|Sochi|Krasnodar|"
    r"St\.?\s*Peterb\w*|G|RUS|RU)\b",
    re.IGNORECASE,
)


def clean_merchant(description: str) -> str:
    """Описание операции → человекочитаемое имя мерчанта."""
    text = re.sub(r"^Оплата в\s+", "", description, flags=re.IGNORECASE)
    text = re.sub(r"^Оплата услуг\s*", "Оплата услуг ", text, flags=re.IGNORECASE)
    text = _CITY_TAIL_RE.sub(" ", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" .,")
    return text or description


def normalize_phone(text: str) -> str | None:
    """Телефон в описании → 10 цифр, чтобы разные записи схлопнулись в одного человека."""
    if m := _PHONE_RE.search(text):
        return "".join(m.groups())
    return None


def detect_kind(description: str, amount) -> tuple[str, str | None]:
    """Вид операции и ключ контрагента для взаимозачёта."""
    low = description.lower()

    if any(p in low for p in _CASH_PATTERNS):
        return KIND_CASH, None
    if any(p in low for p in _CASHBACK_PATTERNS):
        return KIND_CASHBACK, None

    if any(p in low for p in _SELF_PATTERNS):
        # Свои счета различаем по номеру договора, а «Кубышку» – по имени.
        if m := _CONTRACT_RE.search(low):
            return KIND_SELF, f"договор {m.group(1)}"
        if "кубышк" in low:
            return KIND_SELF, "Кубышка"
        return KIND_SELF, "свой счёт"

    if any(p in low for p in _PERSON_PATTERNS):
        if phone := normalize_phone(description):
            return KIND_PERSON, phone
        # Входящий СБП не содержит отправителя – сваливаем в общий пул.
        return KIND_PERSON, "сбп-без-номера"

    if any(p in low for p in _INCOME_PATTERNS) and amount > 0:
        return KIND_INCOME, None

    return KIND_PURCHASE, None


def categorize(transaction: Transaction) -> Transaction:
    """Проставить операции вид, категорию и контрагента."""
    kind, counterparty = detect_kind(transaction.description, transaction.amount)
    transaction.kind = kind
    transaction.counterparty = counterparty

    if kind == KIND_SELF or kind == KIND_PERSON:
        transaction.category = M.TRANSFER
        return transaction
    if kind == KIND_CASHBACK:
        transaction.category = M.CASHBACK
        return transaction
    if kind == KIND_INCOME:
        transaction.category = M.REFUND if "возврат" in transaction.description.lower() else M.INCOME
        return transaction
    if kind == KIND_CASH:
        transaction.category = M.CASH
        return transaction

    # Приход, не опознанный как доход, всё равно не расход.
    if transaction.amount > 0:
        transaction.category = M.INCOME
        return transaction

    if category := M.category_for_mcc(transaction.mcc):
        transaction.category = category
        return transaction

    low = transaction.description.lower()
    for keyword, category in _MERCHANTS:
        if keyword in low:
            transaction.category = category
            return transaction

    for pattern, category in _PATTERN_RULES:
        if pattern.search(transaction.description):
            transaction.category = category
            return transaction

    transaction.category = M.OTHER
    return transaction


def categorize_all(transactions: list[Transaction]) -> list[Transaction]:
    return [categorize(t) for t in transactions]
