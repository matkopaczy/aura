"""Raport tygodniowy i alerty (§8.2). Tekst prosty, jeden ekran telefonu."""

import datetime
import logging
import smtplib
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.attribution import summarize
from app.config import get_settings
from app.i18n import render_factor, t
from app.models import (
    CurationStatus,
    Event,
    Market,
    Property,
    Recommendation,
    RecommendationStatus,
    ReportKind,
    ReportSent,
    User,
)

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        raise RuntimeError("SMTP nie jest skonfigurowany (SMTP_HOST) — nie wysyłam")
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_user and settings.smtp_password:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def render_weekly_report(db: Session, prop: Property, locale: str = "pl") -> tuple[str, str]:
    """Zwraca (temat, treść) raportu tygodniowego dla obiektu."""
    market = db.get(Market, prop.market_id)
    today = datetime.datetime.now(ZoneInfo(market.timezone)).date()
    horizon = today + datetime.timedelta(days=14)

    pending = db.scalars(
        select(Recommendation)
        .where(
            Recommendation.property_id == prop.id,
            Recommendation.status == RecommendationStatus.PENDING,
            Recommendation.stay_date >= today,
            Recommendation.stay_date <= horizon,
        )
        .order_by(Recommendation.stay_date)
    ).all()

    lines = [t("email.weekly.greeting", locale=locale), ""]
    if pending:
        lines.append(t("email.weekly.pending_header", locale=locale, count=len(pending)))
        for rec in pending:
            factors = rec.explanation_params.get("factors", [])
            reason = ", ".join(render_factor(f, locale=locale) for f in factors[:2])
            lines.append(
                t(
                    "email.weekly.pending_line",
                    locale=locale,
                    date=rec.stay_date.isoformat(),
                    previous=rec.previous_price,
                    price=rec.recommended_price,
                    reason=reason or "-",
                )
            )
    else:
        lines.append(t("email.weekly.no_pending", locale=locale))

    week_ago = today - datetime.timedelta(days=7)
    result = summarize(db, prop, since=week_ago)
    lines += [
        "",
        t("email.weekly.result_header", locale=locale),
        t(
            "email.weekly.result_line",
            locale=locale,
            accepted=result.accepted_count,
            delta=result.extra_revenue,
        ),
    ]

    top_event = db.scalar(
        select(Event)
        .where(
            Event.market_id == prop.market_id,
            Event.curation_status == CurationStatus.APPROVED,
            Event.start_date >= today,
            Event.start_date <= today + datetime.timedelta(days=60),
        )
        .order_by(Event.impact_strength.desc())
        .limit(1)
    )
    if top_event is not None:
        lines += [
            "",
            t("email.weekly.event_header", locale=locale),
            t(
                "email.weekly.event_line",
                locale=locale,
                name=top_event.name,
                start=top_event.start_date.isoformat(),
                end=top_event.end_date.isoformat(),
            ),
        ]

    lines += ["", t("email.weekly.cta", locale=locale, url=get_settings().dashboard_url)]
    subject = t("email.weekly.subject", locale=locale, pending=len(pending))
    return subject, "\n".join(lines)


def send_weekly_reports(db: Session) -> int:
    """Wysyła raport tygodniowy każdemu użytkownikowi z obiektami. Zwraca liczbę maili."""
    sent = 0
    users = db.scalars(select(User).where(User.is_active.is_(True))).all()
    for user in users:
        properties = db.scalars(
            select(Property).where(Property.account_id == user.account_id)
        ).all()
        for prop in properties:
            subject, body = render_weekly_report(db, prop, locale=user.locale)
            send_email(user.email, subject, body)
            db.add(
                ReportSent(
                    account_id=user.account_id,
                    kind=ReportKind.WEEKLY,
                    sent_at=datetime.datetime.now(datetime.UTC),
                    meta={"property_id": str(prop.id), "to": user.email},
                )
            )
            sent += 1
    db.commit()
    logger.info("Raporty tygodniowe: wysłano %d", sent)
    return sent
