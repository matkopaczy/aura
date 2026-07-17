"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { OccupancyPoint, getPublicOccupancy } from "@/lib/api";

// Kolor mapy = mediana ceny za dobę (dostępna wszędzie, gdzie jest scraping).
// Obłożenie wymaga skanów wyczerpujących i bywa None — pokazujemy je w etykiecie,
// gdy znane. Sekwencyjna skala jednego koloru (magnituda): jasny -> ciemny.
const PRICE_BINS: { min: number; fill: string }[] = [
  { min: 750, fill: "#17641f" },
  { min: 550, fill: "#3c8a47" },
  { min: 400, fill: "#6fae72" },
  { min: 300, fill: "#a9cfa9" },
  { min: 0, fill: "#d7e8d7" },
];
const NO_DATA_FILL = "#ffffff";
const NO_DATA_STROKE = "#b5b5b5";

function fillFor(median: number | null): { fill: string; stroke: string } {
  if (median === null) return { fill: NO_DATA_FILL, stroke: NO_DATA_STROKE };
  const bin = PRICE_BINS.find((b) => median >= b.min) ?? PRICE_BINS[PRICE_BINS.length - 1];
  return { fill: bin.fill, stroke: "#0b3d14" };
}

// Uproszczony kontur Polski (lng, lat) — orientacyjny, wystarczający do mapy punktowej.
const OUTLINE: [number, number][] = [
  [14.20, 53.90], [16.00, 54.50], [17.00, 54.80], [18.30, 54.83], [18.95, 54.35],
  [19.65, 54.45], [20.50, 54.35], [22.80, 54.36], [23.50, 54.20], [23.93, 53.90],
  [23.50, 53.00], [23.60, 52.60], [23.20, 52.30], [23.65, 52.10], [23.60, 51.50],
  [24.10, 50.85], [23.90, 50.40], [23.00, 49.98], [22.65, 49.50], [22.00, 49.20],
  [21.00, 49.40], [20.10, 49.20], [19.80, 49.20], [19.45, 49.60], [18.85, 49.52],
  [18.35, 49.95], [17.70, 50.30], [16.90, 50.45], [16.20, 50.40], [15.00, 51.00],
  [14.80, 50.87], [14.98, 51.33], [14.60, 51.80], [14.75, 52.06], [14.60, 52.60],
  [14.12, 52.84],
];

const LNG = { min: 14.0, max: 24.3 };
const LAT = { min: 49.0, max: 55.0 };
const WIDTH = 560;
// Korekta proporcji: 1° długości ≈ cos(52°) szerokości w tych stronach.
const HEIGHT = Math.round(
  (WIDTH * (LAT.max - LAT.min)) / ((LNG.max - LNG.min) * Math.cos((52 * Math.PI) / 180))
);

function x(lng: number): number {
  return ((lng - LNG.min) / (LNG.max - LNG.min)) * WIDTH;
}
function y(lat: number): number {
  return ((LAT.max - lat) / (LAT.max - LAT.min)) * HEIGHT;
}

function medianOf(p: OccupancyPoint): number | null {
  return p.median_price !== null ? Number(p.median_price) : null;
}

function pointTitle(
  p: OccupancyPoint,
  t: (key: string, params?: Record<string, string | number>) => string
): string {
  const median = medianOf(p);
  if (median === null) return `${p.name}: ${t("mapNoData")}`;
  const price = t("mapPricePerNight", { price: Math.round(median) });
  return p.occupancy !== null
    ? `${p.name}: ${price}, ${t("mapOccupancy", { pct: Math.round(p.occupancy * 100) })}`
    : `${p.name}: ${price}`;
}

export default function PolandOccupancyMap() {
  const t = useTranslations("home");
  const [points, setPoints] = useState<OccupancyPoint[]>([]);

  useEffect(() => {
    getPublicOccupancy().then(setPoints).catch(() => setPoints([]));
  }, []);

  if (points.length === 0) return null;

  const outlinePath =
    OUTLINE.map(
      ([lng, lat], i) => `${i === 0 ? "M" : "L"}${x(lng).toFixed(1)},${y(lat).toFixed(1)}`
    ).join(" ") + " Z";
  // Etykiety bezpośrednie tylko dla najdroższych rynków — bez zaśmiecania mapy.
  const labeled = points
    .filter((p) => medianOf(p) !== null)
    .sort((a, b) => (medianOf(b) as number) - (medianOf(a) as number))
    .slice(0, 6);

  return (
    <section style={{ marginTop: "2rem" }}>
      <h2>{t("mapTitle")}</h2>
      <p style={{ color: "#555" }}>{t("mapSubtitle")}</p>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        style={{ width: "100%", maxWidth: 560 }}
        role="img"
        aria-label={t("mapTitle")}
      >
        <path d={outlinePath} fill="#f4f6f4" stroke="#c9d2c9" strokeWidth="1.5" />
        {points.map((p) => {
          const median = medianOf(p);
          const { fill, stroke } = fillFor(median);
          return (
            <a key={p.slug} href={`/rynek/${p.slug}`}>
              <circle
                cx={x(p.center_lng)}
                cy={y(p.center_lat)}
                r={median !== null ? 9 : 5}
                fill={fill}
                stroke={stroke}
                strokeWidth="1.5"
              >
                <title>{pointTitle(p, t)}</title>
              </circle>
            </a>
          );
        })}
        {labeled.map((p) => (
          <text
            key={p.slug}
            x={x(p.center_lng) + 12}
            y={y(p.center_lat) + 4}
            fontSize="12"
            fill="#1a1a2e"
          >
            {p.name} {Math.round(medianOf(p) as number)} zł
          </text>
        ))}
      </svg>
      <div
        style={{
          display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap",
          fontSize: "0.85rem", color: "#555",
        }}
      >
        <span>{t("mapLegendLow")}</span>
        {[...PRICE_BINS].reverse().map((b) => (
          <span
            key={b.min}
            style={{
              width: 22, height: 12, background: b.fill,
              display: "inline-block", borderRadius: 3,
            }}
          />
        ))}
        <span>{t("mapLegendHigh")}</span>
        <span style={{ marginLeft: "0.75rem", display: "inline-flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 12, height: 12, background: NO_DATA_FILL,
              border: `1.5px solid ${NO_DATA_STROKE}`, borderRadius: "50%",
              display: "inline-block",
            }}
          />
          {t("mapNoData")}
        </span>
      </div>
    </section>
  );
}
