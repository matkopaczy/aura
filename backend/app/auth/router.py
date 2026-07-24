from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log as audit_log
from app.auth.deps import CurrentUser
from app.auth.security import create_access_token, hash_password, verify_password
from app.billing import start_trial
from app.config import get_settings
from app.db import get_db
from app.models import Account, User
from app.password_reset import apply_reset, request_reset, resolve

router = APIRouter(prefix="/api/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


class RegisterRequest(BaseModel):
    account_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: str
    email: str
    account_id: str
    locale: str
    role: str
    is_curator: bool


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: DbSession) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == body.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_taken")

    account = Account(name=body.account_name)
    db.add(account)
    db.flush()
    user = User(
        account_id=account.id,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    start_trial(db, account)  # 30 dni bez karty od rejestracji (§5)
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, account.id))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    audit_log(db, user.account_id, user.id, "login")
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.account_id))


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=str(user.id),
        email=user.email,
        account_id=str(user.account_id),
        locale=user.locale,
        role=user.role,
        is_curator=user.is_curator,
    )


class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    detail: str = "if_exists_sent"


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
def password_reset_request(
    body: PasswordResetRequestBody, db: DbSession
) -> PasswordResetRequestResponse:
    """Zawsze ten sam komunikat — nigdy nie zdradzamy, czy konto istnieje (§9)."""
    token = request_reset(db, body.email)
    if token is not None:
        user = db.scalar(select(User).where(User.email == body.email.lower()))
        audit_log(db, user.account_id, user.id, "password_reset_requested")
        db.commit()
        settings = get_settings()
        if settings.smtp_host:
            from app.emails import send_email
            from app.i18n import t

            url = f"{settings.dashboard_url}/reset-password?token={token}"
            send_email(
                to=body.email.lower(),
                subject=t("email.password_reset.subject"),
                body=t("email.password_reset.body", url=url),
            )
    return PasswordResetRequestResponse()


class PasswordResetConfirmBody(BaseModel):
    token: str
    new_password: str = Field(min_length=10, max_length=200)


@router.post("/password-reset/confirm", response_model=TokenResponse)
def password_reset_confirm(body: PasswordResetConfirmBody, db: DbSession) -> TokenResponse:
    """Ustawia nowe hasło i od razu loguje (jak rejestracja)."""
    token, user, error = resolve(db, body.token)
    if error is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    apply_reset(db, token, user, body.new_password)  # commituje samo (patrz password_reset.py)
    audit_log(db, user.account_id, user.id, "password_reset_confirmed")
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.account_id))
