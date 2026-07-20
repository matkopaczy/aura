"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  ApiError,
  EventItem,
  Market,
  MonitoringResponse,
  getMarketEvents,
  getMarketMonitoring,
  getMarkets,
} from "@/lib/api";
import DemandCalendar from "@/components/DemandCalendar";

function formatOccupancy(value: number | null, noData: string): string {
  return value === null ? noData : `${Math.round(value * 100)}%`;
}

// Podaż rynku (A5): trend liczby ofert między migawkami. Strzałka + znak
// czytelne; próg 3% odsiewa szum pomiaru.
function formatSupplyTrend(pct: number): string {
  if (pct >= 3) return `▲ +${pct}% konkurencji`;
  if (pct <= -3) return `▼ ${pct}% konkurencji`;
  return "→ podaż stabilna";
}

// Tempo rynku (A4): pace to zmiana presji w pkt proc. Znak + strzałka czytelne
// dla przeciętnej osoby; próg 3 pp odsiewa szum.
function formatPace(value: number | null): string {
  if (value === null) return "—";
  const pp = Math.round(value * 100);
  if (pp >= 3) return `↑ +${pp} pp`;
  if (pp <= -3) return `↓ ${pp} pp`;
  return "→ bez zmian";
}

export default function MonitoringPage() {
  const t = useTranslations("monitoring");
  const [markets, setMarkets] = useState<Market[]>([]);
  const [slug, setSlug] = useState<string>("");
  const [data, setData] = useState<MonitoringResponse | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [guests, setGuests] = useState<number>(2); // 2-os. (domyślnie) / 1-os.
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
      window.location.href = "/login";
      return;
    }
    setError("loadError");
  }, []);

  useEffect(() => {
    getMarkets()
      .then((list) => {
        setMarkets(list);
        if (list.length > 0) setSlug(list[0].slug);
      })
      .catch(handleError);
  }, [handleError]);

  useEffect(() => {
    if (!slug) return;
    Promise.all([getMarketMonitoring(slug, 30, guests), getMarketEvents(slug)])
      .then(([monitoring, marketEvents]) => {
        setData(monitoring);
        setEvents(marketEvents);
      })
      .catch(handleError);
  }, [slug, guests, handleError]);

  return (
    <main>
      <h1>{t("title")}</h1>
      <label htmlFor="market">{t("selectMarket")}</label>
      <select
        id="market"
        value={slug}
        onChange={(e) => {
          setError(null); // stary błąd nie dotyczy nowo wybranego rynku
          setSlug(e.target.value);
        }}
      >
        {markets.map((m) => (
          <option key={m.slug} value={m.slug}>
            {m.name}
          </option>
        ))}
      </select>

      <fieldset style={{ border: "none", padding: "0.5rem 0", margin: 0 }}>
        <legend style={{ padding: 0, fontSize: "0.9rem", color: "#555" }}>
          {t("guestsLabel")}
        </legend>
        <label style={{ marginRight: "1rem" }}>
          <input
            type="radio"
            name="guests"
            checked={guests === 2}
            onChange={() => setGuests(2)}
          />{" "}
          {t("guests2")}
        </label>
        <label>
          <input
            type="radio"
            name="guests"
            checked={guests === 1}
            onChange={() => setGuests(1)}
          />{" "}
          {t("guests1")}
        </label>
      </fieldset>

      {guests === 1 && <p className="hint">{t("singlesHint")}</p>}

      {error !== null && <p className="error">{t(error)}</p>}

      {data !== null && (
        <DemandCalendar days={data.days} events={events} currencyCode={data.currency_code} />
      )}

      {data !== null && data.supply_total !== null && (
        <p className="hint">
          {t("supplyLine", { count: data.supply_total })}
          {data.supply_previous !== null &&
            data.supply_previous !== 0 &&
            ` ${formatSupplyTrend(
              Math.round(
                ((data.supply_total - data.supply_previous) / data.supply_previous) * 100,
              ),
            )}`}
        </p>
      )}

      {data !== null && data.floor_min !== null && data.floor_median !== null && (
        <p className="hint">
          {t("spreadLine", {
            min: Number(data.floor_min).toFixed(0),
            median: Number(data.floor_median).toFixed(0),
            currency: data.currency_code,
            spread: Math.round(
              ((Number(data.floor_median) - Number(data.floor_min)) /
                Number(data.floor_min)) *
                100,
            ),
          })}
        </p>
      )}

      {data !== null && (
        <table>
          <thead>
            <tr>
              <th>{t("date")}</th>
              <th>{t("median")}</th>
              <th>{t("priceBand")}</th>
              <th>{t("pace")}</th>
              <th>{t("sample")}</th>
              <th>{t("occupancy")}</th>
            </tr>
          </thead>
          <tbody>
            {data.days.map((day) => (
              <tr key={day.stay_date}>
                <td>{day.stay_date}</td>
                <td>
                  {day.median_price !== null
                    ? `${Number(day.median_price).toFixed(0)} ${data.currency_code}`
                    : t("noData")}
                </td>
                <td>
                  {day.price_p25 !== null && day.price_p75 !== null
                    ? `${Number(day.price_p25).toFixed(0)}–${Number(day.price_p75).toFixed(0)} ${data.currency_code}`
                    : "—"}
                </td>
                <td>{formatPace(day.booking_pace)}</td>
                <td>{day.sample_size}</td>
                <td>{formatOccupancy(day.occupancy, t("noData"))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>{t("upcomingEvents")}</h2>
      {events.length === 0 ? (
        <p>{t("noEvents")}</p>
      ) : (
        <ul>
          {events.map((event) => (
            <li key={event.id}>
              <strong>{event.name}</strong> ({event.category}) {event.start_date} –{" "}
              {event.end_date}
              {event.district ? `, ${event.district}` : ""}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
