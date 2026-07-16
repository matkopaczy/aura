import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.db import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="invalid_credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise _credentials_error
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
        account_id = uuid.UUID(payload["acc"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise _credentials_error from exc

    # Filtr po account_id z tokenu — izolacja tenantów już na wejściu (§6.2 pkt 1).
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.account_id == account_id,
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise _credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_owner(user: CurrentUser) -> User:
    """Dostęp tylko dla właściciela konta (ceny, rozliczenia, zespół — § role)."""
    from app.models import UserRole

    if user.role != UserRole.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner_required")
    return user


OwnerUser = Annotated[User, Depends(require_owner)]
