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

function formatOccupancy(value: number | null, noData: string): string {
  return value === null ? noData : `${Math.round(value * 100)}%`;
}

export default function MonitoringPage() {
  const t = useTranslations("monitoring");
  const [markets, setMarkets] = useState<Market[]>([]);
  const [slug, setSlug] = useState<string>("");
  const [data, setData] = useState<MonitoringResponse | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
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
    setError(null);
    Promise.all([getMarketMonitoring(slug, 30), getMarketEvents(slug)])
      .then(([monitoring, marketEvents]) => {
        setData(monitoring);
        setEvents(marketEvents);
      })
      .catch(handleError);
  }, [slug, handleError]);

  return (
    <main>
      <h1>{t("title")}</h1>
      <label htmlFor="market">{t("selectMarket")}</label>
      <select id="market" value={slug} onChange={(e) => setSlug(e.target.value)}>
        {markets.map((m) => (
          <option key={m.slug} value={m.slug}>
            {m.name}
          </option>
        ))}
      </select>

      {error !== null && <p className="error">{t(error)}</p>}

      {data !== null && (
        <table>
          <thead>
            <tr>
              <th>{t("date")}</th>
              <th>{t("median")}</th>
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
