"""Проверка взаимозачёта на примерах, которые задал владелец приложения."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app import netting
from app.models import KIND_PERSON, KIND_SELF, KIND_PURCHASE, Transaction


def tx(amount: str, kind: str, counterparty: str | None = None, desc: str = "тест") -> Transaction:
    return Transaction(
        date=datetime(2026, 8, 1, 12, 0),
        amount=Decimal(amount),
        description=desc,
        kind=kind,
        counterparty=counterparty,
    )


def test_долг_другу_вернули_полностью():
    """Дал 500, вернули 500 – не потрачено ничего."""
    res = netting.compute([
        tx("-500", KIND_PERSON, "9001234567"),
        tx("+500", KIND_PERSON, "9001234567"),
    ])
    assert res.net_expense == Decimal(0)
    assert res.gross_expense == Decimal(500)
    assert res.saved_by_netting == Decimal(500)


def test_долг_другу_вернули_частично():
    """Дал 500, вернули 300 – потрачено 200."""
    res = netting.compute([
        tx("-500", KIND_PERSON, "9001234567"),
        tx("+300", KIND_PERSON, "9001234567"),
    ])
    assert res.net_expense == Decimal(200)


def test_долги_разных_людей_не_гасят_друг_друга():
    """Васе дал 500 и не вернули, Петя прислал 500 – это не зачёт."""
    res = netting.compute([
        tx("-500", KIND_PERSON, "9001111111"),
        tx("+500", KIND_PERSON, "9002222222"),
    ])
    assert res.net_expense == Decimal(500)
    assert res.net_income == Decimal(500)


def test_кредитка_взял_100_вернул_110():
    """Пришло 100 с кредитки, ушло 110 обратно – потрачено 10 на обслуживание долга."""
    res = netting.compute(
        [
            tx("+100", KIND_SELF, "кредитка"),
            tx("-110", KIND_SELF, "кредитка"),
        ],
        account_types={"кредитка": netting.ACC_CREDIT},
    )
    assert res.net_expense == Decimal(10)
    assert res.debt_repaid == Decimal(10)


def test_кредитка_взял_100к_вернул_92к_это_рост_долга():
    """Взял 100к, вернул 92к – долг вырос на 8к, но это не доход и не расход."""
    res = netting.compute(
        [
            tx("+100000", KIND_SELF, "кредитка"),
            tx("-92000", KIND_SELF, "кредитка"),
        ],
        account_types={"кредитка": netting.ACC_CREDIT},
    )
    assert res.debt_increased == Decimal(8000)
    assert res.net_expense == Decimal(0)
    assert res.net_income == Decimal(0)


def test_кредитка_взял_92к_вернул_100к_это_погашение():
    """Обратная ситуация: выплачено 8к долга, и это настоящий расход."""
    res = netting.compute(
        [
            tx("+92000", KIND_SELF, "кредитка"),
            tx("-100000", KIND_SELF, "кредитка"),
        ],
        account_types={"кредитка": netting.ACC_CREDIT},
    )
    assert res.debt_repaid == Decimal(8000)
    assert res.net_expense == Decimal(8000)


def test_накопительный_счёт_это_сбережения_а_не_трата():
    """Отложил 10к на накопительный – деньги не потрачены."""
    res = netting.compute(
        [tx("-10000", KIND_SELF, "Кубышка")],
        account_types={"Кубышка": netting.ACC_SAVINGS},
    )
    assert res.net_expense == Decimal(0)
    assert res.saved_to_savings == Decimal(10000)


def test_снятие_из_накоплений_не_доход():
    res = netting.compute(
        [tx("+10000", KIND_SELF, "Кубышка")],
        account_types={"Кубышка": netting.ACC_SAVINGS},
    )
    assert res.net_income == Decimal(0)
    assert res.taken_from_savings == Decimal(10000)


def test_свои_счета_не_схлопываются_между_собой():
    """Ушло на один счёт, пришло с другого – это разные счета, общий котёл недопустим."""
    res = netting.compute(
        [
            tx("-100000", KIND_SELF, "договор 111"),
            tx("+92000", KIND_SELF, "договор 222"),
        ],
        account_types={"договор 111": netting.ACC_CREDIT, "договор 222": netting.ACC_CREDIT},
        # Оба счёта считаются уже опознанными (выписки по ним загружены) –
        # иначе заметный перевод на неопознанный счёт сначала требует уточнения.
        linked_contracts={"111", "222"},
    )
    assert res.debt_repaid == Decimal(100000)
    assert res.debt_increased == Decimal(92000)


def test_обычные_покупки_считаются_полностью():
    res = netting.compute([
        tx("-1000", KIND_PURCHASE, desc="Магнит"),
        tx("-500", KIND_PURCHASE, desc="Пятёрочка"),
    ])
    assert res.net_expense == Decimal(1500)
    assert res.saved_by_netting == Decimal(0)


def test_копеечное_расхождение_считается_нулём():
    """Сальдо в пределах рубля – округление, а не трата."""
    res = netting.compute([
        tx("-500.30", KIND_PERSON, "9001234567"),
        tx("+500.00", KIND_PERSON, "9001234567"),
    ])
    assert res.net_expense == Decimal(0)


def test_ручная_пометка_настоящего_расхода():
    """Пользователь сказал: это подарок, а не долг – зачёт не применять."""
    res = netting.compute(
        [
            tx("-500", KIND_PERSON, "9001234567"),
            tx("+500", KIND_PERSON, "9001234567"),
        ],
        overrides={"9001234567": netting.OVERRIDE_EXPENSE},
    )
    assert res.net_expense == Decimal(500)


def test_объединение_кредитки_названной_по_разному():
    """Банк зовёт одну кредитку двумя именами: исходящие «на договор N»,
    входящие «Перевод себе». Без объединения сальдо считается по половине потока."""
    txs = [
        tx("+92561.40", KIND_SELF, "свой счёт", desc="Перевод себе"),
        tx("-100400", KIND_SELF, "договор 0441828088", desc="Внутренний перевод"),
    ]
    merged = netting.compute(
        txs,
        account_types={"кредитка": netting.ACC_CREDIT},
        merge_groups={"свой счёт": "кредитка", "договор 0441828088": "кредитка"},
    )
    assert merged.debt_repaid == Decimal("7838.60")
    assert merged.net_expense == Decimal("7838.60")

    split = netting.compute(
        txs,
        account_types={"договор 0441828088": netting.ACC_CREDIT, "свой счёт": netting.ACC_CREDIT},
        linked_contracts={"0441828088"},
    )
    assert split.debt_repaid == Decimal("100400")


def test_мелкий_перевод_на_неопознанный_счёт_не_спрашивается():
    """Раз выписка одна, мелкие внутренние движения безопасно нейтральны –
    вопрос пользователю не задаётся вовсе."""
    res = netting.compute([
        tx("-2000", KIND_SELF, "договор 999", desc="Внутренний перевод"),
        tx("-50000", KIND_PURCHASE, desc="Аренда"),
    ])
    assert res.accounts_pending_choice() == []
    assert res.net_expense == Decimal(50000)  # перевод не в счёт трат


def test_крупный_перевод_на_неопознанный_счёт_требует_уточнения():
    """Заметная доля оборота на счёт без выписки – нужно спросить, чей он,
    а не тихо угадывать."""
    res = netting.compute([
        tx("-80000", KIND_SELF, "договор 999", desc="Внутренний перевод"),
        tx("-20000", KIND_PURCHASE, desc="Аренда"),
    ])
    pending = res.accounts_pending_choice()
    assert len(pending) == 1
    assert pending[0].key == "договор 999"
    # Пока не уточнено – в расход эта сумма не идёт (не гадаем).
    assert res.net_expense == Decimal(20000)


def test_ответ_мой_второй_счёт_ждёт_выписку():
    """Пользователь подтвердил, что счёт свой – просим выписку, а сальдо
    временно не считаем расходом, чтобы не соврать цифрой."""
    res = netting.compute(
        [
            tx("-80000", KIND_SELF, "договор 999", desc="Внутренний перевод"),
            tx("-20000", KIND_PURCHASE, desc="Аренда"),
        ],
        account_owner={"договор 999": netting.OWNER_SELF},
    )
    assert res.accounts_pending_choice() == []
    waiting = res.accounts_pending_upload()
    assert len(waiting) == 1 and waiting[0].key == "договор 999"
    assert res.net_expense == Decimal(20000)


def test_ответ_счёт_другого_человека_зачитывается_автоматически():
    """«Чужой счёт» – дальше это обычный перевод человеку, без ручной разметки."""
    res = netting.compute(
        [
            tx("-80000", KIND_SELF, "договор 999", desc="Внутренний перевод"),
            tx("+80000", KIND_SELF, "договор 999", desc="Перевод средств из"),
            tx("-20000", KIND_PURCHASE, desc="Аренда"),
        ],
        account_owner={"договор 999": netting.OWNER_OTHER},
    )
    assert res.net_expense == Decimal(20000)  # 80к туда-обратно – взаимозачёт
    assert any(p.key == "договор 999" for p in res.people())


def test_счёт_с_загруженной_выпиской_сразу_можно_классифицировать():
    """Если по счёту уже загружена выписка – тип выбирается сразу,
    без промежуточного вопроса «чей это счёт»."""
    res = netting.compute(
        [
            tx("-80000", KIND_SELF, "договор 999", desc="Внутренний перевод"),
            tx("-20000", KIND_PURCHASE, desc="Аренда"),
        ],
        account_types={"договор 999": netting.ACC_CREDIT},
        linked_contracts={"999"},
    )
    assert res.accounts_pending_choice() == []
    assert res.debt_repaid == Decimal(80000)
