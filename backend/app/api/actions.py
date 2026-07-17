"""One-tap decyzja z e-maila bez logowania (§8.2).

GET pokazuje lekką stronę potwierdzenia (bezpieczna — bez mutacji, odporna na
prefetch skanerów poczty), POST wykonuje decyzję. Teksty z szablonów (§6.2 pkt 5).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.action_tokens import apply_token, resolve
from app.config import get_settings
from app.db import get_db
from app.i18n import t
from app.models import ActionTokenAction

router = APIRouter(prefix="/api/actions", tags=["actions"])

DbSession = Annotated[Session, Depends(get_db)]

LOCALE = "pl"


def _page(body: str, status_code: int = 200) -> HTMLResponse:
    dashboard = get_settings().dashboard_url
    html = f"""<!doctype html>
<html lang="{LOCALE}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t("action.confirm.title", locale=LOCALE)}</title>
<style>
 body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#f4f6f4;
   margin:0;padding:2rem 1rem;color:#1c2b1c}}
 .card{{max-width:28rem;margin:2rem auto;background:#fff;border-radius:12px;padding:2rem;
   box-shadow:0 1px 4px rgba(0,0,0,.08);text-align:center}}
 h1{{font-size:1.2rem;margin:0 0 1rem}}
 button{{font-size:1.05rem;padding:.8rem 1.6rem;border:0;border-radius:8px;background:#2f6b2f;
   color:#fff;cursor:pointer}}
 a{{color:#2f6b2f}}
 .muted{{color:#666;font-size:.9rem;margin-top:1.2rem}}
</style></head>
<body><div class="card">{body}
<p class="muted"><a href="{dashboard}">{t("action.dashboard_link", locale=LOCALE)}</a></p>
</div></body></html>"""
    return HTMLResponse(content=html, status_code=status_code)


def _error_page(error_key: str) -> HTMLResponse:
    msg = t(f"action.error.{error_key}", locale=LOCALE)
    return _page(f"<h1>{msg}</h1>", status_code=410 if error_key != "invalid" else 404)


@router.get("/{raw_token}", response_class=HTMLResponse)
def confirm_page(raw_token: str, db: DbSession) -> HTMLResponse:
    token, rec, error = resolve(db, raw_token)
    if error is not None:
        return _error_page(error)
    q_key = (
        "action.confirm.accept_question"
        if token.action == ActionTokenAction.ACCEPT
        else "action.confirm.reject_question"
    )
    btn_key = (
        "action.confirm.button_accept"
        if token.action == ActionTokenAction.ACCEPT
        else "action.confirm.button_reject"
    )
    question = t(q_key, locale=LOCALE, price=rec.recommended_price, date=rec.stay_date.isoformat())
    button = t(btn_key, locale=LOCALE)
    body = (
        f"<h1>{question}</h1>"
        f'<form method="post" action="/api/actions/{raw_token}">'
        f'<button type="submit">{button}</button></form>'
    )
    return _page(body)


@router.post("/{raw_token}", response_class=HTMLResponse)
def apply_page(raw_token: str, db: DbSession) -> HTMLResponse:
    token, rec, error = resolve(db, raw_token)
    if error is not None:
        return _error_page(error)
    apply_token(db, token, rec)
    done_key = (
        "action.done.accepted"
        if token.action == ActionTokenAction.ACCEPT
        else "action.done.rejected"
    )
    msg = t(done_key, locale=LOCALE, price=rec.recommended_price, date=rec.stay_date.isoformat())
    return _page(f"<h1>{msg}</h1>")
