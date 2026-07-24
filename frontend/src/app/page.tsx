"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  ApiError,
  MarketPreview,
  PublicMarket,
  getMarketPreview,
  getPublicMarkets,
  joinWaitlist,
} from "@/lib/api";
import PolandOccupancyMap from "@/components/PolandOccupancyMap";
import FactorWaterfall from "@/components/FactorWaterfall";
import { Recommendation } from "@/lib/api";

// Przykład poglądowy (§6.2 pkt 5, uczciwość produktu): NIE prawdziwe dane
// użytkownika — landing nie ma zalogowanego konta. Jawnie oznaczony w UI jako
// "Przykład" (t("exampleTitle")). Liczby zgodne z realną matematyką silnika
// (weekend ×1.10, sezon wysoki ×1.10, zaokrąglenie do 5 zł) — ten sam mechanizm
// co w panelu, nie fikcyjna dekoracja.
const EXAMPLE_RECOMMENDATION: Recommendation = {
  id: "example",
  property_id: "example",
  stay_date: "2026-08-14",
  recommended_price: "485",
  previous_price: "350",
  currency_code: "PLN",
  status: "pending",
  explanation_template_key: "v1",
  explanation_params: {
    median: "410",
    factors: [
      { key: "event", pct: 15, name: "Weekend z Wniebowzięciem NMP" },
      { key: "weekend", pct: 10 },
      { key: "high_season", pct: 10 },
    ],
  },
  decided_at: null,
};

function averageMedian(preview: MarketPreview): number | null {
  const values = preview.days
    .map((d) => (d.median_price ? Number(d.median_price) : null))
    .filter((v): v is number => v !== null);
  if (values.length === 0) return null;
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
}

export default function HomePage() {
  const t = useTranslations("home");
  const [markets, setMarkets] = useState<PublicMarket[]>([]);
  const [slug, setSlug] = useState("");
  const [preview, setPreview] = useState<MarketPreview | null>(null);
  const [email, setEmail] = useState("");
  const [joined, setJoined] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPublicMarkets()
      .then((list) => {
        setMarkets(list);
        if (list.length > 0) setSlug(list[0].slug);
      })
      .catch(() => setError("loadError"));
  }, []);

  async function showMarket() {
    setError(null);
    setJoined(false);
    try {
      setPreview(await getMarketPreview(slug));
    } catch {
      setError("loadError");
    }
  }

  async function join(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await joinWaitlist(email, slug);
      setJoined(true);
    } catch (e) {
      setError(e instanceof ApiError ? "loadError" : "loadError");
    }
  }

  const avg = preview ? averageMedian(preview) : null;

  return (
    <main style={{ maxWidth: 760 }}>
      <h1>{t("title")}</h1>
      <p>{t("subtitle")}</p>

      <section
        style={{
          margin: "1.5rem 0",
          padding: "1.25rem 1.5rem",
          background: "#fff",
          border: "1px solid #dbe5db",
          borderRadius: 8,
        }}
      >
        <span
          style={{
            display: "inline-block",
            fontSize: "0.75rem",
            fontWeight: 700,
            letterSpacing: "0.03em",
            color: "#2f6b2f",
            background: "#e7f3e7",
            padding: "0.15rem 0.5rem",
            borderRadius: 4,
            marginBottom: "0.5rem",
          }}
        >
          {t("exampleBadge")}
        </span>
        <h2 style={{ margin: "0 0 0.2rem" }}>{t("exampleTitle")}</h2>
        <p style={{ color: "#555", marginTop: 0 }}>{t("exampleHint")}</p>
        <FactorWaterfall rec={EXAMPLE_RECOMMENDATION} />
      </section>

      <ul>
        <li>{t("sell1")}</li>
        <li>{t("sell2")}</li>
        <li>{t("sell3")}</li>
        <li>{t("sell4")}</li>
      </ul>
      <p>
        <Link href="/register">
          <button type="button">{t("register")}</button>
        </Link>{" "}
        <Link href="/login">{t("cta")}</Link>
      </p>

      <section style={{ marginTop: "2.5rem", padding: "1.5rem", background: "#f0f7f0", borderRadius: 8 }}>
        <h2>{t("leadTitle")}</h2>
        <p>{t("leadSubtitle")}</p>
        <label htmlFor="market">{t("selectMarket")}</label>
        <select id="market" value={slug} onChange={(e) => setSlug(e.target.value)}>
          {markets.map((m) => (
            <option key={m.slug} value={m.slug}>
              {m.name}
            </option>
          ))}
        </select>
        <button type="button" onClick={showMarket}>
          {t("show")}
        </button>

        {error !== null && <p className="error">{t(error)}</p>}

        {preview !== null && (
          <div style={{ marginTop: "1rem" }}>
            <h3>{preview.market_name}</h3>
            <p>
              <strong>{t("avgMedian")}:</strong>{" "}
              {avg !== null ? `${avg} ${preview.currency_code}` : "—"}
            </p>
            {preview.floor !== null && (
              <p>
                {t("floorLine", {
                  min: Number(preview.floor.min_price).toFixed(0),
                  currency: preview.currency_code,
                  sample: preview.floor.sample_size,
                })}
              </p>
            )}
            {preview.coverage_level === "recommendations" ? (
              <p>{t("coverageRecommendations")}</p>
            ) : (
              <>
                <p>{t("coverageMonitoring")}</p>
                {joined ? (
                  <p>{t("waitlistDone")}</p>
                ) : (
                  <form onSubmit={join}>
                    <input
                      type="email"
                      placeholder={t("waitlistEmail")}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                    <button type="submit">{t("waitlistJoin")}</button>
                  </form>
                )}
              </>
            )}
          </div>
        )}
      </section>

      <PolandOccupancyMap />

      {markets.some((m) => m.coverage_level === "recommendations") && (
        <section style={{ marginTop: "2rem" }}>
          <h2>{t("reportsTitle")}</h2>
          <p>{t("reportsSubtitle")}</p>
          <ul>
            {markets
              .filter((m) => m.coverage_level === "recommendations")
              .map((m) => (
                <li key={m.slug}>
                  <Link href={`/rynek/${m.slug}`}>{m.name}</Link>
                </li>
              ))}
          </ul>
        </section>
      )}
    </main>
  );
}
