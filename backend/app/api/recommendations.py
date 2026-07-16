import datetime
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.engine import compute_recommendation
from app.models import (
    CoverageLevel,
    CurationStatus,
    Event,
    Market,
    Property,
    Recommendation,
    RecommendationStatus,
)
from app.models.base import utcnow
from app.monitoring import market_series

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

DbSession = Annotated[Session, Depends(get_db)]


class RecommendationResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    stay_date: datetime.date
    recommended_price: Decimal
    previous_price: Decimal | None
    currency_code: str
    status: RecommendationStatus
    explanation_template_key: str
    explanation_params: dict
    decided_at: datetime.datetime | None


class DecisionRequest(BaseModel):
    decision: Literal["accepted", "rejected"]


class AttributionResponse(BaseModel):
    accepted_count: int
    sold_count: int
    extra_revenue: Decimal
    currency_code: str


def _to_response(rec: Recommendation) -> RecommendationResponse:
    return RecommendationResponse(
        id=rec.id,
        property_id=rec.property_id,
        stay_date=rec.stay_date,
        recommended_price=rec.recommended_price,
        previous_price=rec.previous_price,
        currency_code=rec.currency_code,
        status=rec.status,
        explanation_template_key=rec.explanation_template_key,
        explanation_params=rec.explanation_params,
        decided_at=rec.decided_at,
    )


def _own_property(db: Session, user, property_id: uuid.UUID) -> Property:
    prop = db.scalar(
        select(Property).where(
            Property.id == property_id,
            Property.account_id == user.account_id,  # izolacja tenantów (§6.2 pkt 1)
        )
    )
    if prop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="property_not_found")
    return prop


def generate_for_property(db: Session, prop: Property, days: int = 60) -> list[Recommendation]:
    market = db.get(Market, prop.market_id)
    if market.coverage_level != CoverageLevel.RECOMMENDATIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="market_monitoring_only"
        )
    if prop.base_price is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="base_price_required"
        )

    events = db.scalars(
        select(Event).where(
            Event.market_id == market.id,
            Event.curation_status == CurationStatus.APPROVED,
        )
    ).all()
    series = market_series(db, market, days=days)
    existing = {
        rec.stay_date: rec
        for rec in db.scalars(
            select(Recommendation).where(
                Recommendation.property_id == prop.id,
                Recommendation.stay_date >= series[0].stay_date,
                Recommendation.stay_date <= series[-1].stay_date,
            )
        )
    }

    result: list[Recommendation] = []
    for day in series:
        draft = compute_recommendation(prop, day.stay_date, day, events)
        rec = existing.get(day.stay_date)
        if rec is not None and rec.status != RecommendationStatus.PENDING:
            continue  # decyzja klienta zapadła — stan zostaje pod atrybucję
        if rec is None:
            rec = Recommendation(
                account_id=prop.account_id,
                property_id=prop.id,
                stay_date=draft.stay_date,
                currency_code=prop.currency_code,
                recommended_price=draft.price,
                previous_price=draft.previous_price,
                explanation_template_key=draft.explanation_template_key,
                explanation_params=draft.explanation_params,
            )
            db.add(rec)
        else:
            rec.recommended_price = draft.price
            rec.previous_price = draft.previous_price
            rec.explanation_template_key = draft.explanation_template_key
            rec.explanation_params = draft.explanation_params
        result.append(rec)
    db.commit()
    return result


@router.post("/{property_id}/generate", response_model=list[RecommendationResponse])
def generate(
    property_id: uuid.UUID, user: CurrentUser, db: DbSession, days: int = 60
) -> list[RecommendationResponse]:
    prop = _own_property(db, user, property_id)
    return [_to_response(r) for r in generate_for_property(db, prop, days=days)]


@router.get("/{property_id}", response_model=list[RecommendationResponse])
def list_recommendations(
    property_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    status_filter: RecommendationStatus | None = None,
) -> list[RecommendationResponse]:
    prop = _own_property(db, user, property_id)
    query = select(Recommendation).where(Recommendation.property_id == prop.id)
    if status_filter is not None:
        query = query.where(Recommendation.status == status_filter)
    recs = db.scalars(query.order_by(Recommendation.stay_date)).all()
    return [_to_response(r) for r in recs]


@router.get("/attribution/{property_id}", response_model=AttributionResponse)
def attribution(
    property_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> AttributionResponse:
    from app.attribution import summarize, update_outcomes

    prop = _own_property(db, user, property_id)
    update_outcomes(db, prop)
    summary = summarize(db, prop)
    return AttributionResponse(
        accepted_count=summary.accepted_count,
        sold_count=summary.sold_count,
        extra_revenue=summary.extra_revenue,
        currency_code=prop.currency_code,
    )


@router.post("/decision/{recommendation_id}", response_model=RecommendationResponse)
def decide(
    recommendation_id: uuid.UUID,
    body: DecisionRequest,
    user: CurrentUser,
    db: DbSession,
) -> RecommendationResponse:
    rec = db.scalar(
        select(Recommendation).where(
            Recommendation.id == recommendation_id,
            Recommendation.account_id == user.account_id,
        )
    )
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="recommendation_not_found"
        )
    if rec.status != RecommendationStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already_decided")
    rec.status = RecommendationStatus(body.decision)
    rec.decided_at = utcnow()
    db.commit()
    return _to_response(rec)
