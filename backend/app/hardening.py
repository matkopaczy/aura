"""Hardening produkcyjny (§9, §10 Sprint 5): nagłówki, rate limit, Sentry.

Rate limiter jest w pamięci procesu — wystarcza dla pilota na jednej maszynie
(§6.1). Współdzielony licznik (Redis) dopiero przy realnej skali (§11).
"""

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-XSS-Protection": "0",
}

# Rate limit tylko dla ścieżek uwierzytelniania (ochrona przed brute force).
# password-reset/request: bez limitu ktoś mógłby zalewać cudzą skrzynkę e-mailami.
# password-reset/confirm: bez limitu ktoś mógłby brute-force'ować token (mimo że
# 32 losowe bajty czynią to praktycznie niewykonalne — obrona w głąb).
RATE_LIMITED_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/password-reset/request",
    "/api/auth/password-reset/confirm",
}
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW_S = 60

# Licznik w pamięci procesu, wspólny dla instancji middleware (§6.1, pilot na 1 maszynie).
_auth_hits: dict[str, deque] = defaultdict(deque)


def reset_rate_limit() -> None:
    """Czyści licznik — używane w testach dla izolacji."""
    _auth_hits.clear()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in RATE_LIMITED_PATHS:
            client = request.client.host if request.client else "unknown"
            now = time.monotonic()
            hits = _auth_hits[client]
            while hits and hits[0] <= now - RATE_LIMIT_WINDOW_S:
                hits.popleft()
            if len(hits) >= RATE_LIMIT_MAX:
                return JSONResponse(
                    status_code=429, content={"detail": "too_many_requests"}
                )
            hits.append(now)
        return await call_next(request)


def init_sentry() -> None:
    """Inicjalizuje Sentry tylko przy ustawionym DSN (§11 — bez infry na zapas)."""
    dsn = get_settings().sentry_dsn
    if not dsn:
        return
    import sentry_sdk

    sentry_sdk.init(dsn=dsn, environment=get_settings().app_env, traces_sample_rate=0.0)


def apply_hardening(app: FastAPI) -> None:
    init_sentry()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuthRateLimitMiddleware)
