"""Справочник MCC-кодов.

MCC – четырёхзначный код типа торговой точки. В выписке Т-Банка отдельной
колонки с ним нет, но он встречается внутри описаний Яндекса
(«YANDEX*5411*LAVKA»), а выписки некоторых других банков дают его явно.
Где код есть – он надёжнее, чем угадывание по названию магазина.
"""

from __future__ import annotations

# Категории расходов
FOOD = "Продукты"
CAFE = "Кафе и рестораны"
TRANSPORT = "Транспорт"
HOUSING = "Жильё и ЖКУ"
HEALTH = "Здоровье"
CLOTHES = "Одежда и красота"
FUN = "Развлечения"
BETS = "Ставки"
GYM = "Спортзал"
CONNECT = "Связь и интернет"
SUBS = "Подписки"
EDU = "Образование"
SERVICES = "Услуги"
TRANSFER = "Переводы"
CASH = "Наличные"
OTHER = "Прочее"

# Нерасходные категории
INCOME = "Доход"
CASHBACK = "Кэшбэк и бонусы"
REFUND = "Возвраты"

ALL_EXPENSE_CATEGORIES = [
    FOOD, CAFE, TRANSPORT, HOUSING, HEALTH, CLOTHES,
    FUN, BETS, GYM, CONNECT, SUBS, EDU, SERVICES, TRANSFER, CASH, OTHER,
]

# Траты, без которых в принципе можно обойтись – база для совета об экономии.
# Спортзал сюда не входит: это вложение в здоровье, а не импульсивная трата.
OPTIONAL_CATEGORIES = {CAFE, FUN, BETS, SUBS, CLOTHES}

# Точные коды имеют приоритет над диапазонами.
_EXACT: dict[str, str] = {
    "4111": TRANSPORT,   # пригородный транспорт, электрички
    "4112": TRANSPORT,   # железные дороги
    "4121": TRANSPORT,   # такси
    "4131": TRANSPORT,   # автобусы
    "4784": TRANSPORT,   # платные дороги
    "4814": CONNECT,     # телефония
    "4816": CONNECT,     # интернет-услуги
    "4899": CONNECT,     # кабельное и платное ТВ
    "4900": HOUSING,     # коммунальные услуги
    "5411": FOOD,        # супермаркеты
    "5412": FOOD,
    "5422": FOOD,        # мясные лавки
    "5441": FOOD,        # кондитерские
    "5451": FOOD,        # молочные
    "5462": FOOD,        # пекарни
    "5499": FOOD,        # продуктовые «у дома»
    "5541": TRANSPORT,   # АЗС
    "5542": TRANSPORT,
    "5811": CAFE,        # кейтеринг
    "5812": CAFE,        # рестораны
    "5813": CAFE,        # бары
    "5814": CAFE,        # фастфуд
    "5815": SUBS,        # цифровой контент
    "5816": SUBS,        # игры по подписке
    "5817": SUBS,        # приложения
    "5818": SUBS,
    "5912": HEALTH,      # аптеки
    "5921": FOOD,        # алкомаркеты
    "5941": FUN,         # спорттовары
    "5942": EDU,         # книжные
    "5977": CLOTHES,     # косметика
    "5691": CLOTHES,
    "5651": CLOTHES,
    "5661": CLOTHES,     # обувь
    "7011": OTHER,       # отели
    "7230": CLOTHES,     # парикмахерские
    "7297": HEALTH,      # массаж
    "7298": HEALTH,      # спа
    "7832": FUN,         # кинотеатры
    "7841": FUN,         # видеопрокат
    "7922": FUN,         # театры и концерты
    "7991": FUN,         # музеи
    "7994": FUN,         # игровые залы, видеоигры
    "7995": BETS,        # азартные игры и ставки
    "7997": GYM,         # клубы, фитнес
    "7999": FUN,
    "7941": GYM,         # спортивные клубы
    "8011": HEALTH,      # врачи
    "8021": HEALTH,      # стоматология
    "8043": HEALTH,      # оптика
    "8062": HEALTH,      # больницы
    "8071": HEALTH,      # лаборатории
    "8211": EDU,         # школы
    "8220": EDU,         # вузы
    "8299": EDU,         # курсы
    "8351": EDU,         # детские сады
    "6010": CASH,        # выдача наличных в банке
    "6011": CASH,        # банкомат
    "4829": TRANSFER,    # денежные переводы
    "6012": TRANSFER,    # финансовые учреждения
    "6536": TRANSFER,    # p2p-переводы
    "6537": TRANSFER,
    "6538": TRANSFER,
    "6540": TRANSFER,
}

# Диапазоны на случай кодов, которых нет в точном списке.
_RANGES: list[tuple[int, int, str]] = [
    (3000, 3299, TRANSPORT),   # авиакомпании
    (3300, 3499, TRANSPORT),   # прокат авто
    (3500, 3999, OTHER),       # отели
    (4000, 4199, TRANSPORT),
    (5300, 5399, FOOD),        # оптовые клубы
    (5600, 5699, CLOTHES),
    (5800, 5899, CAFE),
    (5900, 5999, OTHER),
    (7000, 7099, OTHER),
    (7200, 7299, CLOTHES),
    (7800, 7999, FUN),
    (8000, 8099, HEALTH),
    (8200, 8299, EDU),
]


def category_for_mcc(mcc: str | None) -> str | None:
    """MCC → категория. None, если код неизвестен или не задан."""
    if not mcc:
        return None
    code = mcc.strip()
    if not code.isdigit() or len(code) != 4:
        return None
    if hit := _EXACT.get(code):
        return hit
    value = int(code)
    for low, high, category in _RANGES:
        if low <= value <= high:
            return category
    return None
