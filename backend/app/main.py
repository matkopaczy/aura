from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.events import router as events_router
from app.api.monitoring import router as monitoring_router
from app.api.properties import router as properties_router
from app.auth.router import router as auth_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()  # fail fast: brak konfiguracji = brak startu
    app = FastAPI(title="Aura API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(properties_router)
    app.include_router(events_router)
    app.include_router(monitoring_router)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
