import { ExplanationFactor } from "@/lib/api";

type Translate = (key: string, params?: Record<string, string | number>) => string;

/** Renderuje czynnik rekomendacji z szablonu tłumaczeń (§6.2 pkt 5). */
export function renderFactor(t: Translate, factor: ExplanationFactor): string {
  const params: Record<string, string | number> = { pct: factor.pct };
  if (factor.name !== undefined) params.name = factor.name;
  if (factor.occupancy !== undefined) {
    params.occupancyPct = Math.round(factor.occupancy * 100);
    params.freePct = Math.round((1 - factor.occupancy) * 100);
  }
  if (factor.position !== undefined) {
    params.positionPct = Math.abs(Math.round(factor.position * 100));
  }
  // Event z miejscem wydarzenia -> szablon z odległością (§ event-distance).
  if (factor.key === "event" && factor.venue_distance_km !== undefined) {
    params.km = factor.venue_distance_km;
    return t("event_venue", params);
  }
  return t(factor.key, params);
}

export function renderExplanation(t: Translate, factors: ExplanationFactor[]): string {
  return factors.map((factor) => renderFactor(t, factor)).join(", ");
}
