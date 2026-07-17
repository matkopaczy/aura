import datetime
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.models import CurationStatus, Event, Market, User

router = APIRouter(prefix="/api", tags=["events"])

DbSession = Annotated[Session, Depends(get_db)]


def require_curator(user: CurrentUser) -> User:
    if not user.is_curator:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="curator_required")
    return user


Curator = Annotated[User, Depends(require_curator)]


class EventCreate(BaseModel):
    market_slug: str
    name: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=50)
    district: str | None = Field(default=None, max_length=100)
    start_date: datetime.date
    end_date: datetime.date
    impact_strength: float = Field(ge=0, le=1)
    source: str = Field(min_length=1, max_length=100)
    curation_status: CurationStatus = CurationStatus.DRAFT
    venue_lat: float | None = Field(default=None, ge=-90, le=90)
    venue_lng: float | None = Field(default=None, ge=-180, le=180)


class EventUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    district: str | None = Field(default=None, max_length=100)
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    impact_strength: float | None = Field(default=None, ge=0, le=1)
    curation_status: CurationStatus | None = None
    venue_lat: float | None = Field(default=None, ge=-90, le=90)
    venue_lng: float | None = Field(default=None, ge=-180, le=180)


class EventResponse(BaseModel):
    id: uuid.UUID
    market_slug: str
    name: str
    category: str
    district: str | None
    start_date: datetime.date
    end_date: datetime.date
    impact_strength: float
    source: str
    curation_status: CurationStatus
    venue_lat: float | None
    venue_lng: float | None


def _to_response(event: Event, market: Market) -> EventResponse:
    return EventResponse(
        id=event.id,
        market_slug=market.slug,
        name=event.name,
        category=event.category,
        district=event.district,
        start_date=event.start_date,
        end_date=event.end_date,
        impact_strength=float(event.impact_strength),
        source=event.source,
        curation_status=event.curation_status,
        venue_lat=float(event.venue_lat) if event.venue_lat is not None else None,
        venue_lng=float(event.venue_lng) if event.venue_lng is not None else None,
    )


def _get_market(db: Session, slug: str) -> Market:
    market = db.scalar(select(Market).where(Market.slug == slug))
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="market_not_found")
    return market


@router.get("/events/{market_slug}", response_model=list[EventResponse])
def list_market_events(
    market_slug: str, user: CurrentUser, db: DbSession
) -> list[EventResponse]:
    """Zatwierdzone, nadchodzące eventy rynku — do wyświetlania klientom."""
    market = _get_market(db, market_slug)
    events = db.scalars(
        select(Event)
        .where(
            Event.market_id == market.id,
            Event.curation_status == CurationStatus.APPROVED,
            Event.end_date >= datetime.date.today(),
        )
        .order_by(Event.start_date)
    ).all()
    return [_to_response(e, market) for e in events]


@router.get("/curation/events/{market_slug}", response_model=list[EventResponse])
def curation_list(market_slug: str, curator: Curator, db: DbSession) -> list[EventResponse]:
    """Wszystkie eventy rynku, każdy status — widok kuratora."""
    market = _get_market(db, market_slug)
    events = db.scalars(
        select(Event).where(Event.market_id == market.id).order_by(Event.start_date)
    ).all()
    return [_to_response(e, market) for e in events]


@router.post(
    "/curation/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED
)
def curation_create(body: EventCreate, curator: Curator, db: DbSession) -> EventResponse:
    market = _get_market(db, body.market_slug)
    if body.end_date < body.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_before_start"
        )
    event = Event(
        market_id=market.id,
        name=body.name,
        category=body.category,
        district=body.district,
        start_date=body.start_date,
        end_date=body.end_date,
        impact_strength=body.impact_strength,
        source=body.source,
        curation_status=body.curation_status,
        venue_lat=body.venue_lat,
        venue_lng=body.venue_lng,
    )
    db.add(event)
    db.commit()
    return _to_response(event, market)


@router.patch("/curation/events/{event_id}", response_model=EventResponse)
def curation_update(
    event_id: uuid.UUID, body: EventUpdate, curator: Curator, db: DbSession
) -> EventResponse:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event_not_found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    if event.end_date < event.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_before_start"
        )
    db.commit()
    market = db.get(Market, event.market_id)
    return _to_response(event, market)


class BulkDecision(BaseModel):
    event_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    status: Literal["approved", "rejected"]


@router.post("/curation/events/bulk")
def curation_bulk(body: BulkDecision, curator: Curator, db: DbSession) -> dict:
    """Masowe zatwierdzanie/odrzucanie — kurator ogarnia setki DRAFT-ów w minuty."""
    result = db.execute(
        update(Event)
        .where(Event.id.in_(body.event_ids))
        .values(curation_status=CurationStatus(body.status))
    )
    db.commit()
    return {"updated": result.rowcount}


@router.post("/curation/events/refresh", status_code=status.HTTP_202_ACCEPTED)
def curation_refresh(curator: Curator, background: BackgroundTasks) -> dict:
    """Odświeża kandydatów na eventy ze wszystkich źródeł (w tle — scraping trwa)."""
    from app.event_sources.ingest import run

    background.add_task(run)
    return {"status": "started"}
