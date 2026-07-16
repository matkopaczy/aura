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
    </main>
  );
}
