"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  ApiError,
  Attribution,
  MonitoringResponse,
  Property,
  Recommendation,
  decideRecommendation,
  generateRecommendations,
  getAttribution,
  getProperties,
  getPropertyMonitoring,
  getRecommendations,
} from "@/lib/api";
import { renderExplanation } from "@/lib/explanations";
import SubscriptionBanner from "@/components/SubscriptionBanner";

function MedianChart({
  monitoring,
  basePrice,
  labels,
}: {
  monitoring: MonitoringResponse;
  basePrice: number | null;
  labels: { yourPrice: string; median: string };
}) {
  const width = 640;
  const height = 180;
  const points = monitoring.days
    .map((day, i) => ({ i, median: day.median_price ? Number(day.median_price) : null }))
    .filter((p) => p.median !== null) as { i: number; median: number }[];
  const values = points.map((p) => p.median).concat(basePrice ? [basePrice] : []);
  if (values.length === 0) return null;
  const max = Math.max(...values) * 1.1;
  const x = (i: number) => (i / Math.max(monitoring.days.length - 1, 1)) * width;
  const y = (v: number) => height - (v / max) * height;
  const polyline = points.map((p) => `${x(p.i).toFixed(1)},${y(p.median).toFixed(1)}`).join(" ");
  return (
    <svg
      viewBox={`0 0 ${width} ${height + 20}`}
      style={{ width: "100%", background: "#fff", border: "1px solid #e0e0e0" }}
      role="img"
    >
      {basePrice !== null && (
        <line x1="0" y1={y(basePrice)} x2={width} y2={y(basePrice)} stroke="#1a7f37" strokeDasharray="6 4" strokeWidth="2" />
      )}
      <polyline points={polyline} fill="none" stroke="#1a1a2e" strokeWidth="2" />
      <text x="4" y={height + 14} fontSize="11" fill="#1a1a2e">
        ● {labels.median}
      </text>
      {basePrice !== null && (
        <text x="160" y={height + 14} fontSize="11" fill="#1a7f37">
          --- {labels.yourPrice}
        </text>
      )}
    </svg>
  );
}

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const te = useTranslations("explanations");
  const [properties, setProperties] = useState<Property[] | null>(null);
  const [propertyId, setPropertyId] = useState("");
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [monitoring, setMonitoring] = useState<MonitoringResponse | null>(null);
  const [attribution, setAttribution] = useState<Attribution | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
      window.location.href = "/login";
      return;
    }
    setError("loadError");
  }, []);

  useEffect(() => {
    getProperties()
      .then((list) => {
        setProperties(list);
        if (list.length > 0) setPropertyId(list[0].id);
      })
      .catch(handleError);
  }, [handleError]);

  const reload = useCallback(() => {
    if (!propertyId) return;
    Promise.all([
      getRecommendations(propertyId),
      getPropertyMonitoring(propertyId, 60),
      getAttribution(propertyId),
    ])
      .then(([recs, mon, attr]) => {
        setRecommendations(recs);
        setMonitoring(mon);
        setAttribution(attr);
      })
      .catch(handleError);
  }, [propertyId, handleError]);

  useEffect(reload, [reload]);

  async function decide(id: string, decision: "accepted" | "rejected") {
    try {
      await decideRecommendation(id, decision);
      reload();
    } catch (e) {
      handleError(e);
    }
  }

  async function refresh() {
    try {
      await generateRecommendations(propertyId, 60);
      reload();
    } catch (e) {
      handleError(e);
    }
  }

  if (properties !== null && properties.length === 0) {
    return (
      <main>
        <h1>{t("title")}</h1>
        <p>{t("noProperty")}</p>
        <a href="/onboarding">
          <button type="button">{t("goOnboarding")}</button>
        </a>
      </main>
    );
  }

  const property = properties?.find((p) => p.id === propertyId) ?? null;
  const basePrice = property?.base_price ? Number(property.base_price) : null;
  const statusLabel: Record<Recommendation["status"], string> = {
    pending: t("statusPending"),
    accepted: t("statusAccepted"),
    rejected: t("statusRejected"),
    expired: t("statusExpired"),
  };
  const medianByDate = new Map(
    (monitoring?.days ?? []).map((d) => [d.stay_date, d.median_price]),
  );

  return (
    <main style={{ maxWidth: 900 }}>
      <h1>{t("title")}</h1>
      <SubscriptionBanner />
      {error !== null && <p className="error">{t(error)}</p>}

      {properties !== null && properties.length > 1 && (
        <>
          <label htmlFor="property">{t("property")}</label>
          <select
            id="property"
            value={propertyId}
            onChange={(e) => setPropertyId(e.target.value)}
          >
            {properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </>
      )}

      {attribution !== null && (
        <section style={{ background: "#f0f7f0", padding: "1rem", borderRadius: 8, marginBottom: "1.5rem" }}>
          <strong>{t("counterTitle")}</strong>
          <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", margin: "0.5rem 0" }}>
            <div>
              <small style={{ color: "#2f6b2f" }}>{t("counterConservativeLabel")}</small>
              <p style={{ fontSize: "1.8rem", margin: "0.1rem 0", fontWeight: 700 }}>
                {Number(attribution.conservative_revenue).toFixed(0)} {attribution.currency_code}
              </p>
              <small>{t("counterConservativeSold", { count: attribution.conservative_sold_count })}</small>
            </div>
            <div style={{ opacity: 0.75 }}>
              <small>{t("counterFullLabel")}</small>
              <p style={{ fontSize: "1.4rem", margin: "0.1rem 0" }}>
                {Number(attribution.extra_revenue).toFixed(0)} {attribution.currency_code}
              </p>
              <small>
                {t("counterAccepted", { count: attribution.accepted_count })},{" "}
                {t("counterSold", { count: attribution.sold_count })}
              </small>
            </div>
          </div>
          <small style={{ display: "block", color: "#555" }}>{t("counterConservativeHint")}</small>
        </section>
      )}

      {monitoring !== null && (
        <section>
          <h2>{t("chartTitle")}</h2>
          <MedianChart
            monitoring={monitoring}
            basePrice={basePrice}
            labels={{ yourPrice: t("chartYourPrice"), median: t("chartMedian") }}
          />
        </section>
      )}

      <h2>{t("calendarTitle")}</h2>
      <button type="button" onClick={refresh}>
        {t("refresh")}
      </button>
      <table>
        <thead>
          <tr>
            <th>{t("date")}</th>
            <th>{t("median")}</th>
            <th>{t("recommendation")}</th>
            <th>{t("why")}</th>
            <th>{t("status")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {recommendations.map((rec) => (
            <tr key={rec.id}>
              <td>{rec.stay_date}</td>
              <td>
                {medianByDate.get(rec.stay_date)
                  ? `${Number(medianByDate.get(rec.stay_date)).toFixed(0)} ${rec.currency_code}`
                  : t("noData")}
              </td>
              <td>
                <strong>
                  {Number(rec.recommended_price).toFixed(0)} {rec.currency_code}
                </strong>
                {rec.previous_price !== null &&
                  ` (${Number(rec.previous_price).toFixed(0)})`}
              </td>
              <td>{renderExplanation(te, rec.explanation_params.factors)}</td>
              <td>{statusLabel[rec.status]}</td>
              <td>
                {rec.status === "pending" && (
                  <>
                    <button type="button" onClick={() => decide(rec.id, "accepted")}>
                      {t("accept")}
                    </button>{" "}
                    <button type="button" onClick={() => decide(rec.id, "rejected")}>
                      {t("reject")}
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
