"use client";

import { useTranslations } from "next-intl";
import { Recommendation } from "@/lib/api";

// Wodospad ceny: jak z ceny bazowej powstaje rekomendacja (§7.1 — "wiesz DLACZEGO").
// UCZCIWIE: czynniki mnożą się (silnik jest multiplikatywny), a końcowy słupek
// "zaokrąglenie i pozostałe" domyka do PRAWDZIWEJ ceny (top-3 to nie wszystkie
// czynniki + zaokrąglenie do 5 zł + ograniczenia min/max). Zero zmyślonej dekompozycji.
const UP = "#3c8a47";
const DOWN = "#d85a30";
const TOTAL = "#4a5a4a";

interface Bar {
  label: string;
  lo: number;
  hi: number;
  fill: string;
  delta: number | null; // null dla słupków baza/cena
}

export default function FactorWaterfall({ rec }: { rec: Recommendation }) {
  const t = useTranslations("waterfall");
  const base = rec.previous_price !== null ? Number(rec.previous_price) : null;
  const recommended = Number(rec.recommended_price);
  if (base === null) return null;

  let running = base;
  const steps: { label: string; before: number; after: number }[] = [];
  for (const f of rec.explanation_params.factors) {
    const before = running;
    running = running * (1 + f.pct / 100);
    steps.push({ label: t(`factor.${f.key}`), before, after: running });
  }
  const reconcile = recommended - running;
  if (Math.abs(reconcile) >= 1) {
    steps.push({ label: t("reconcile"), before: running, after: recommended });
  }

  const bars: Bar[] = [
    { label: t("base"), lo: 0, hi: base, fill: TOTAL, delta: null },
    ...steps.map((s) => ({
      label: s.label,
      lo: Math.min(s.before, s.after),
      hi: Math.max(s.before, s.after),
      fill: s.after >= s.before ? UP : DOWN,
      delta: Math.round(s.after - s.before),
    })),
    { label: t("price"), lo: 0, hi: recommended, fill: TOTAL, delta: null },
  ];

  const maxV = Math.max(base, recommended, ...steps.map((s) => Math.max(s.before, s.after))) * 1.14;
  const barW = 56;
  const gap = 10;
  const plotH = 150;
  const labelH = 46;
  const width = bars.length * (barW + gap) + gap;
  const height = plotH + labelH;
  const y = (v: number) => plotH - (v / maxV) * plotH;
  const cur = rec.currency_code;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ maxWidth: "100%", height: "auto" }}
      role="img"
      aria-label={t("aria", { from: Math.round(base), to: Math.round(recommended), currency: cur })}
    >
      {bars.map((b, i) => {
        const x = gap + i * (barW + gap);
        const top = y(b.hi);
        const barHeight = Math.max(2, y(b.lo) - y(b.hi));
        return (
          <g key={i}>
            <rect x={x} y={top} width={barW} height={barHeight} rx={3} fill={b.fill} />
            <text x={x + barW / 2} y={top - 4} textAnchor="middle" fontSize="11" fill="#1c2b1c">
              {b.delta === null
                ? `${Math.round(b.hi)} ${cur}`
                : `${b.delta > 0 ? "+" : ""}${b.delta}`}
            </text>
            <text
              x={x + barW / 2}
              y={plotH + 16}
              textAnchor="middle"
              fontSize="11"
              fill="#555"
            >
              {b.label.length > 12 ? b.label.slice(0, 11) + "…" : b.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
