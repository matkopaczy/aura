import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import {
  averageMedian,
  averageOccupancy,
  fetchMarketPreview,
  fetchPublicMarkets,
} from "@/lib/publicServer";

// Pre-render raportów dla miast pierwszej fali (coverage=recommendations, §5.2).
// Inne rynki renderują się na żądanie (dynamicParams domyślnie true).
export async function generateStaticParams() {
  const markets = await fetchPublicMarkets();
  return markets
    .filter((m) => m.coverage_level === "recommendations")
    .map((m) => ({ slug: m.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const t = await getTranslations("marketReport");
  const preview = await fetchMarketPreview(slug);
  if (preview === null) return { title: t("metaTitle", { city: slug }) };
  const median = averageMedian(preview);
  const description =
    median !== null
      ? t("metaDescription", {
          city: preview.market_name,
          median,
          currency: preview.currency_code,
        })
      : t("metaDescriptionNoData", { city: preview.market_name });
  return {
    title: t("metaTitle", { city: preview.market_name }),
    description,
    alternates: { canonical: `/rynek/${slug}` },
    openGraph: {
      title: t("metaTitle", { city: preview.market_name }),
      description,
    },
  };
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("pl-PL", { day: "numeric", month: "short", weekday: "short" });
}

export default async function MarketReportPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const t = await getTranslations("marketReport");
  const preview = await fetchMarketPreview(slug);
  if (preview === null) notFound();

  const median = averageMedian(preview);
  const occupancy = averageOccupancy(preview);
  const upcoming = preview.days
    .filter((d) => d.median_price !== null)
    .slice(0, 7);
  const others = (await fetchPublicMarkets()).filter(
    (m) => m.coverage_level === "recommendations" && m.slug !== slug
  );

  return (
    <main style={{ maxWidth: 760 }}>
      <h1>{t("title", { city: preview.market_name })}</h1>
      <p>{t("intro", { city: preview.market_name })}</p>

      {median === null ? (
        <p>{t("noData")}</p>
      ) : (
        <>
          <section
            style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", margin: "1.5rem 0" }}
          >
            <div style={{ background: "#f0f7f0", padding: "1rem 1.25rem", borderRadius: 8 }}>
              <small>{t("avgMedianLabel")}</small>
              <p style={{ fontSize: "1.8rem", margin: "0.2rem 0", fontWeight: 700 }}>
                {median} {preview.currency_code}
              </p>
            </div>
            {occupancy !== null && (
              <div style={{ background: "#f0f7f0", padding: "1rem 1.25rem", borderRadius: 8 }}>
                <small>{t("occupancyLabel")}</small>
                <p style={{ fontSize: "1.8rem", margin: "0.2rem 0", fontWeight: 700 }}>
                  {occupancy}%
                </p>
              </div>
            )}
          </section>

          {preview.floor !== null && (
            <p>
              {t("floorLine", {
                min: Number(preview.floor.min_price).toFixed(0),
                currency: preview.currency_code,
                sample: preview.floor.sample_size,
              })}
            </p>
          )}

          {upcoming.length > 0 && (
            <section style={{ marginTop: "1.5rem" }}>
              <h2>{t("tableTitle")}</h2>
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left" }}>{t("tableDate")}</th>
                      <th style={{ textAlign: "right" }}>{t("tableMedian")}</th>
                      <th style={{ textAlign: "right" }}>{t("tableOccupancy")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {upcoming.map((d) => (
                      <tr key={d.stay_date}>
                        <td>{formatDate(d.stay_date)}</td>
                        <td style={{ textAlign: "right" }}>
                          {Number(d.median_price).toFixed(0)} {preview.currency_code}
                        </td>
                        <td style={{ textAlign: "right" }}>
                          {d.occupancy !== null ? `${Math.round(d.occupancy * 100)}%` : t("na")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}

      <p style={{ marginTop: "1rem" }}>
        {preview.coverage_level === "recommendations"
          ? t("coverageRecommendations")
          : t("coverageMonitoring")}
      </p>
      <p>
        <small>{t("updatedNote")}</small>
      </p>

      <section
        style={{ marginTop: "2rem", padding: "1.5rem", background: "#eef4ff", borderRadius: 8 }}
      >
        <h2 style={{ marginTop: 0 }}>{t("ctaTitle")}</h2>
        <p>{t("ctaText")}</p>
        <Link href="/register">
          <button type="button">{t("ctaButton")}</button>
        </Link>
      </section>

      {others.length > 0 && (
        <p style={{ marginTop: "1.5rem" }}>
          {t("otherCities")}{" "}
          {others.map((m, i) => (
            <span key={m.slug}>
              {i > 0 && ", "}
              <Link href={`/rynek/${m.slug}`}>{m.name}</Link>
            </span>
          ))}
        </p>
      )}
    </main>
  );
}
