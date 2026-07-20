"""Kontrola jakości danych po nocnym przebiegu — ochrona przed cichą degradacją.

Incydenty, które ma wykrywać (oba realne):
- 2026-07-18: martwy parametr offset Bookinga — skan zbierał 1 stronę zamiast 4,
  testy zielone, dane systematycznie ubogie, zero błędów;
- 2026-07-19: wstrzyknięty SSLKEYLOGFILE — 32/32 jobów padło, 0 obserwacji.

Metoda: wolumen obserwacji per rynek w oknie ostatnich 24 h vs poprzednie 24 h.
Spadek poniżej progu = alert e-mail do administratora (jeśli skonfigurowany),
zawsze log WARNING.
"""

import datetime
import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.i18n import t
from app.models import CompetitorListing, Market, PriceObservation

logger = logging.getLogger(__name__)

# Alarm, gdy bieżąca doba ma mniej niż 70% obserwacji poprzedniej doby.
DROP_THRESHOLD = 0.7
# Rynki z mniejszą bazą dobową pomijamy — świeże/małe rynki dają szum.
MIN_BASELINE = 100

LOCALE = "pl"


@dataclass(frozen=True)
class QualityIssue:
    market_slug: str
    previous: int
    current: int

    @property
    def drop_pct(self) -> int:
        return round((self.previous - self.current) / self.previous * 100)


def _counts_by_market(
    db: Session, since: datetime.datetime, until: datetime.datetime
) -> dict[str, int]:
    rows = db.execute(
        select(Market.slug, func.count(PriceObservation.id))
        .join(CompetitorListing, CompetitorListing.market_id == Market.id)
        .join(PriceObservation, PriceObservation.listing_id == CompetitorListing.id)
        .where(
            PriceObservation.guests == 2,  # kontrola jakości głównego skanu 2-os.
            PriceObservation.observed_at >= since,
            PriceObservation.observed_at < until,
        )
        .group_by(Market.slug)
    ).all()
    return dict(rows)


def find_quality_issues(
    db: Session, now: datetime.datetime | None = None
) -> list[QualityIssue]:
    """Rynki, którym w ostatniej dobie ubyło danych względem poprzedniej."""
    now = now or datetime.datetime.now(datetime.UTC)
    day = datetime.timedelta(hours=24)
    current = _counts_by_market(db, now - day, now)
    previous = _counts_by_market(db, now - 2 * day, now - day)

    issues = []
    for market in db.scalars(select(Market)):
        if not market.active_sources:
            continue
        prev = previous.get(market.slug, 0)
        curr = current.get(market.slug, 0)
        if prev >= MIN_BASELINE and curr < prev * DROP_THRESHOLD:
            issues.append(QualityIssue(market.slug, prev, curr))
    return sorted(issues, key=lambda i: i.drop_pct, reverse=True)


def report_quality_issues(db: Session, now: datetime.datetime | None = None) -> int:
    """Loguje i (jeśli skonfigurowano) wysyła alert. Zwraca liczbę problemów."""
    issues = find_quality_issues(db, now)
    if not issues:
        logger.info("kontrola jakości danych: bez zastrzeżeń")
        return 0

    for issue in issues:
        logger.warning(
            "jakość danych %s: %d -> %d obserwacji (-%d%%)",
            issue.market_slug, issue.previous, issue.current, issue.drop_pct,
        )

    settings = get_settings()
    if settings.smtp_host and settings.admin_alert_email:
        from app.emails import send_email

        lines = [t("email.quality.intro", locale=LOCALE)]
        lines += [
            t(
                "email.quality.line",
                locale=LOCALE,
                market=i.market_slug,
                previous=i.previous,
                current=i.current,
                pct=i.drop_pct,
            )
            for i in issues
        ]
        send_email(
            to=settings.admin_alert_email,
            subject=t("email.quality.subject", locale=LOCALE, count=len(issues)),
            body="\n".join(lines),
        )
    return len(issues)
