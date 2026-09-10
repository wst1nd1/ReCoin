"""HTTP-слой ReCoin."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import Cookie, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from . import agent, analytics, auth, fallback, mailer, netting, portfolio
from .categorizer import categorize_all, clean_merchant
from .config import get_settings
from .parser import parse_statement

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SESSION_TTL_SECONDS = 60 * 60 * 3
MAX_SESSIONS = 200
AUTH_COOKIE = "recoin_auth"

app = FastAPI(title="ReCoin")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
auth.init_db()


@dataclass
class Session:
    """Данные одного пользователя. Живут в памяти и стираются по времени."""

    created: float = field(default_factory=time.time)
    statements: list[portfolio.Statement] = field(default_factory=list)
    account_types: dict[str, str] = field(default_factory=dict)
    account_owner: dict[str, str] = field(default_factory=dict)  # "чей это счёт": self | other
    merge_groups: dict[str, str] = field(default_factory=dict)
    answers: dict[str, str] = field(default_factory=dict)
    questions: list[dict] = field(default_factory=list)
    ai_used: bool = False


# Разобранные выписки живут в памяти процесса и привязаны к пользователю:
# на диск финансовые данные не пишутся вообще.
_sessions: dict[int, Session] = {}


def _cleanup() -> None:
    now = time.time()
    stale = [k for k, s in _sessions.items() if now - s.created > SESSION_TTL_SECONDS]
    for key in stale:
        _sessions.pop(key, None)
    while len(_sessions) > MAX_SESSIONS:
        oldest = min(_sessions, key=lambda k: _sessions[k].created)
        _sessions.pop(oldest, None)


def _require_user(token: str | None) -> auth.User:
    user = auth.user_for_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Нужно войти в аккаунт")
    return user


def _get_session(user: auth.User) -> Session:
    _cleanup()
    session = _sessions.get(user.id)
    if session is None:
        session = Session()
        _sessions[user.id] = session
    return session


def _money(value: Decimal | int | float) -> int:
    return int(round(float(value)))


def _asset_version() -> str:
    """Метка для адресов стилей и скриптов.

    Без неё браузер продолжает отдавать файлы из своего хранилища, и правки
    в оформлении не видны до принудительного обновления страницы.
    """
    static = BASE_DIR / "static"
    try:
        newest = max(item.stat().st_mtime for item in static.iterdir() if item.is_file())
    except (OSError, ValueError):
        return "0"
    return str(int(newest))


def _build_state(session: Session) -> dict[str, Any]:
    """Пересчитать всё от загруженных выписок до готовых цифр."""
    folio = portfolio.build(session.statements)
    result = netting.compute(
        folio.transactions,
        account_types=session.account_types,
        merge_groups=session.merge_groups,
        account_owner=session.account_owner,
        linked_contracts=folio.contracts,
    )

    # Мерчанты, которых не осилил словарь, доразбираются моделью.
    unknown = sorted({
        clean_merchant(t.description)
        for t in result.purchases
        if t.amount < 0 and t.category == "Прочее"
    })
    if unknown:
        mapping = agent.categorize_merchants(unknown)
        if mapping:
            session.ai_used = True
            for tx in result.purchases:
                if tx.category == "Прочее":
                    tx.category = mapping.get(clean_merchant(tx.description), "Прочее")

    start, end = folio.period
    report = analytics.analyze(folio.transactions, result, start, end)

    def _account_row(party, with_type: bool = False) -> dict[str, Any]:
        row = {
            "key": party.key,
            "title": party.title,
            "incoming": _money(party.incoming),
            "outgoing": _money(party.outgoing),
            "netto": _money(party.netto),
            "count": party.count,
        }
        if with_type:
            row["type"] = party.account_type
        return row

    # Счета – только те, что реально нужно показать пользователю:
    # с заметным оборотом, опознанные как свои (сразу можно выбрать тип),
    # либо ждущие уточнения "чей это счёт" или загрузки второй выписки.
    # Переводы людям сюда не попадают – они зачитываются автоматически,
    # без отдельного экрана (счета – это про счета, переводы – про переводы).
    accounts = [_account_row(p, with_type=True) for p in result.accounts_to_classify()]
    pending_accounts = [_account_row(p) for p in result.accounts_pending_choice()]
    awaiting_statements = [_account_row(p) for p in result.accounts_pending_upload()]

    return {
        "analysis": report,
        "netting": result,
        "portfolio": folio,
        "payload": {
            "statements": [
                {
                    "label": s.label,
                    "contract": s.report.contract,
                    "period": (
                        f"{s.report.period_start:%d.%m.%Y} – {s.report.period_end:%d.%m.%Y}"
                        if s.report.period_start else ""
                    ),
                    "parsed": s.report.parsed,
                    "bank": s.report.bank,
                    "source": s.report.source,
                    "warnings": s.report.warnings,
                }
                for s in session.statements
            ],
            "notes": folio.notes,
            "internal_pairs": folio.internal_pairs,
            "internal_volume": _money(folio.internal_volume),
            "totals": {
                "gross_expense": _money(report.gross_expense),
                "net_expense": _money(report.net_expense),
                "living_expense": _money(report.living_expense),
                "per_month": _money(report.living_expense / report.months),
                "income": _money(report.income),
                "average_check": _money(report.average_check),
                "operations": report.transactions_count,
                "optional": _money(report.optional_amount),
                "optional_share": round(report.optional_share, 1),
                "weekend_share": round(report.weekend_share, 1),
                "saved_to_savings": _money(report.saved_to_savings),
                "debt_repaid": _money(report.debt_repaid),
                "debt_increased": _money(report.debt_increased),
                "lent_not_returned": _money(report.lent_not_returned),
                "months": float(round(report.months, 1)),
            },
            "categories": [
                {"name": r.name, "amount": _money(r.amount), "share": round(r.share, 1), "count": r.count}
                for r in report.categories
            ],
            "merchants": [
                {"name": r.name, "amount": _money(r.amount), "count": r.count, "category": r.category}
                for r in report.top_merchants
            ],
            "biggest": [
                {
                    "name": clean_merchant(t.description),
                    "amount": _money(t.abs_amount),
                    "date": t.date.strftime("%d.%m.%Y"),
                    "category": t.category,
                }
                for t in report.biggest
            ],
            "regulars": [
                {
                    "name": r.merchant,
                    "average": _money(r.average),
                    "count": r.count,
                    "per_year": _money(r.per_year),
                    "category": r.category,
                }
                for r in report.regulars
            ],
            "monthly": [{"month": m, "amount": _money(v)} for m, v in report.monthly],
            "months_detail": [
                {
                    "key": row.key,
                    "label": row.label,
                    "amount": _money(row.amount),
                    "count": row.count,
                    "top_category": row.top_category,
                    "top_amount": _money(row.top_amount),
                    "delta": round(row.delta, 1) if row.delta is not None else None,
                }
                for row in report.months_detail
            ],
            "accounts": accounts,
            "pending_accounts": pending_accounts,
            "awaiting_statements": awaiting_statements,
            "ai": session.ai_used,
        },
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, recoin_auth: str | None = Cookie(default=None)):
    """Гостю – витрина, вошедшему – сразу рабочий кабинет."""
    if auth.user_for_token(recoin_auth):
        return RedirectResponse("/app", status_code=303)
    return templates.TemplateResponse(
        request, "landing.html", {"request": request, "v": _asset_version()}
    )


@app.get("/app", response_class=HTMLResponse)
async def workspace(request: Request, recoin_auth: str | None = Cookie(default=None)):
    user = auth.user_for_token(recoin_auth)
    if user is None:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request,
        "app.html",
        {
            "request": request,
            "v": _asset_version(),
            "user": {"name": user.name, "email": user.email, "initials": user.initials},
        },
    )


def _auth_response(user: auth.User) -> JSONResponse:
    token = auth.start_session(user.id)
    response = JSONResponse({"ok": True, "user": {"name": user.name, "email": user.email}})
    response.set_cookie(
        AUTH_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=get_settings().https_only,
        max_age=auth.SESSION_TTL_SECONDS,
    )
    return response


@app.post("/api/auth/register")
async def register(body: dict):
    password = body.get("password", "")
    if password != body.get("password_repeat", password):
        raise HTTPException(status_code=400, detail="Пароли не совпадают.")
    try:
        user = auth.register(
            email=body.get("email", ""),
            password=password,
            name=body.get("name", ""),
        )
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _auth_response(user)


@app.post("/api/auth/reset/request")
async def reset_request(body: dict):
    """Выслать код восстановления на почту."""
    email = body.get("email", "")
    issued = auth.create_reset_code(email)

    if issued is not None:
        code, name = issued
        mailer.send_reset_code(auth.normalize_email(email), code, name)

    # Ответ одинаковый независимо от того, есть такая почта или нет,
    # иначе по нему можно перебирать зарегистрированные адреса.
    return JSONResponse({
        "ok": True,
        "message": "Если такая почта зарегистрирована, код отправлен на неё.",
        "mail_configured": mailer.smtp_configured(),
    })


@app.post("/api/auth/reset/confirm")
async def reset_confirm(body: dict):
    """Сменить пароль по коду из письма."""
    password = body.get("password", "")
    if password != body.get("password_repeat", password):
        raise HTTPException(status_code=400, detail="Пароли не совпадают.")
    try:
        user = auth.reset_password(
            email=body.get("email", ""),
            code=body.get("code", ""),
            new_password=password,
        )
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _auth_response(user)


@app.post("/api/auth/login")
async def login(body: dict):
    try:
        user = auth.authenticate(body.get("email", ""), body.get("password", ""))
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _auth_response(user)


@app.post("/api/auth/logout")
async def logout(recoin_auth: str | None = Cookie(default=None)):
    auth.end_session(recoin_auth)
    response = JSONResponse({"ok": True})
    response.delete_cookie(AUTH_COOKIE)
    return response


@app.get("/api/auth/me")
async def me(recoin_auth: str | None = Cookie(default=None)):
    user = auth.user_for_token(recoin_auth)
    if user is None:
        return JSONResponse({"authorized": False})
    return JSONResponse({
        "authorized": True,
        "user": {"name": user.name, "email": user.email, "initials": user.initials},
    })


@app.get("/api/status")
async def status(recoin_auth: str | None = Cookie(default=None)):
    settings = get_settings()
    user = auth.user_for_token(recoin_auth)
    return {
        "ai": settings.ai_available,
        "model": settings.model if settings.ai_available else None,
        "endpoint": settings.base_url or "api.anthropic.com",
        "authorized": user is not None,
    }


@app.post("/api/upload")
async def upload(
    files: list[UploadFile] = File(...),
    recoin_auth: str | None = Cookie(default=None),
):
    """Загрузка одной или нескольких выписок."""
    user = _require_user(recoin_auth)
    session = _get_session(user)
    accepted = 0
    problems: list[str] = []

    for upload_file in files:
        raw = await upload_file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            problems.append(f"{upload_file.filename}: файл больше 25 МБ")
            continue
        if not raw[:5].startswith(b"%PDF"):
            problems.append(f"{upload_file.filename}: это не PDF")
            continue

        try:
            transactions, report = parse_statement(raw)
        except Exception as exc:  # noqa: BLE001 – пользователю нужен понятный текст
            log.exception("разбор не удался")
            problems.append(f"{upload_file.filename}: не удалось прочитать ({exc})")
            continue

        if not transactions:
            problems.append(
                f"{upload_file.filename}: операции не найдены. "
                f"Возможно, это скан или выписка неподдерживаемого банка."
            )
            continue

        report.source = upload_file.filename or "выписка"
        # Повторную загрузку того же счёта за тот же период заменяем, а не дублируем.
        session.statements = [
            s for s in session.statements
            if not (s.report.contract and s.report.contract == report.contract
                    and s.report.period_start == report.period_start)
        ]
        session.statements.append(
            portfolio.Statement(report=report, transactions=categorize_all(transactions))
        )
        accepted += 1

    if not session.statements:
        raise HTTPException(status_code=400, detail="; ".join(problems) or "Не удалось разобрать файлы")

    state = _build_state(session)
    payload = state["payload"]
    payload["problems"] = problems
    payload["accepted"] = accepted
    return JSONResponse(payload)


@app.post("/api/accounts")
async def set_accounts(body: dict, recoin_auth: str | None = Cookie(default=None)):
    """Пользователь уточняет назначение своих счетов: тип известного счёта
    (вклад/кредит/другое) или ответ на вопрос "чей это счёт" для неопознанного."""
    session = _get_session(_require_user(recoin_auth))
    if not session.statements:
        raise HTTPException(status_code=400, detail="Сначала загрузите выписку")

    types = body.get("account_types") or {}
    merges = body.get("merge_groups") or {}
    owner = body.get("account_owner") or {}

    allowed_types = {netting.ACC_SAVINGS, netting.ACC_CREDIT, netting.ACC_NEUTRAL, netting.ACC_UNKNOWN}
    session.account_types = {k: v for k, v in types.items() if v in allowed_types}
    session.merge_groups = {k: v for k, v in merges.items() if isinstance(v, str)}
    allowed_owner = {netting.OWNER_SELF, netting.OWNER_OTHER}
    session.account_owner = {k: v for k, v in owner.items() if v in allowed_owner}

    return JSONResponse(_build_state(session)["payload"])


@app.post("/api/questions")
async def questions(recoin_auth: str | None = Cookie(default=None)):
    """Вопросы под конкретные цифры пользователя."""
    session = _get_session(_require_user(recoin_auth))
    if not session.statements:
        raise HTTPException(status_code=400, detail="Сначала загрузите выписку")

    state = _build_state(session)
    report: analytics.Analysis = state["analysis"]

    items = agent.generate_questions(analytics.to_summary(report))
    if items:
        session.ai_used = True
    else:
        items = fallback.generate_questions(report)

    session.questions = items
    return JSONResponse({"questions": items, "ai": bool(session.ai_used)})


@app.post("/api/report")
async def build_report(body: dict, recoin_auth: str | None = Cookie(default=None)):
    """Итоговый разбор с учётом ответов пользователя."""
    session = _get_session(_require_user(recoin_auth))
    if not session.statements:
        raise HTTPException(status_code=400, detail="Сначала загрузите выписку")

    answers = body.get("answers") or {}
    session.answers = {str(k): str(v)[:500] for k, v in answers.items()}

    state = _build_state(session)
    report: analytics.Analysis = state["analysis"]

    # Вопросы вместе с ответами – чтобы модель видела, на что именно ответили.
    labelled = {}
    for question in session.questions:
        key = question.get("id")
        if key in session.answers:
            labelled[question.get("text", key)] = session.answers[key]

    result = agent.build_report(analytics.to_summary(report), labelled or session.answers)
    if result:
        session.ai_used = True
        result["offline"] = False
    else:
        result = fallback.build_report(report, session.answers)

    return JSONResponse(result)


@app.post("/api/reset")
async def reset(recoin_auth: str | None = Cookie(default=None)):
    """Забыть загруженные выписки, не выходя из аккаунта."""
    user = _require_user(recoin_auth)
    _sessions.pop(user.id, None)
    return {"ok": True}
