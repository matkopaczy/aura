"use client";

import { useTranslations } from "next-intl";
import { EventItem, MonitoringDay } from "@/lib/api";

// Heatmapa popytu (A1/A6): kolor = mediana ceny dnia znormalizowana względem
// zakresu tego rynku w oknie. Gorące dni (drogie względem własnego rynku) =
// ciemniejsze. UCZCIWIE: to realne ceny ofertowe, bez wymyślonej kompozycji
// wag — dokładnie ta sama zielona skala co mapa Polski. Eventy = kropka.
const RAMP = ["#d7e8d7", "#a9cfa9", "#6fae72", "#3c8a47", "#17641f"];
const NO_DATA = "#f1f1f1";

function medianOf(day: MonitoringDay): number | null {
  return day.median_price !== null ? Number(day.median_price) : null;
}

// 5 koszyków wg pozycji dnia w zakresie [min, max] median rynku.
function binIndex(value: number, min: number, max: number): number {
  if (max <= min) return 2; // płaski rynek — środek skali
  const pos = (value - min) / (max - min);
  return Math.min(RAMP.length - 1, Math.floor(pos * RAMP.length));
}

function eventOn(dateISO: string, events: EventItem[]): EventItem | null {
  return events.find((e) => dateISO >= e.start_date && dateISO <= e.end_date) ?? null;
}

interface Props {
  days: MonitoringDay[];
  events: EventItem[];
  currencyCode: string;
}

export default function DemandCalendar({ days, events, currencyCode }: Props) {
  const t = useTranslations("monitoring");
  const medians = days.map(medianOf).filter((m): m is number => m !== null);
  if (medians.length === 0) return null;
  const min = Math.min(...medians);
  const max = Math.max(...medians);

  return (
    <section>
      <h2>{t("demandTitle")}</h2>
      <p className="hint">{t("demandHint")}</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", maxWidth: "640px" }}>
        {days.map((day) => {
          const median = medianOf(day);
          const event = eventOn(day.stay_date, events);
          const fill = median === null ? NO_DATA : RAMP[binIndex(median, min, max)];
          const [, mm, dd] = day.stay_date.split("-");
          const title =
            median === null
              ? `${day.stay_date}: ${t("noData")}`
              : `${day.stay_date}: ${Math.round(median)} ${currencyCode}` +
                (event ? ` — ${event.name}` : "");
          return (
            <div
              key={day.stay_date}
              title={title}
              style={{
                position: "relative",
                width: "38px",
                height: "38px",
                background: fill,
                border: "1px solid #cfd8cf",
                borderRadius: "4px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "11px",
                color: median !== null && binIndex(median, min, max) >= 3 ? "#fff" : "#1c2b1c",
              }}
            >
              {dd}.{mm}
              {event && (
                <span
                  aria-hidden="true"
                  style={{
                    position: "absolute",
                    top: "2px",
                    right: "3px",
                    fontSize: "9px",
                    lineHeight: 1,
                  }}
                >
                  ●
                </span>
              )}
            </div>
          );
        })}
      </div>
      <p className="hint" style={{ marginTop: "8px" }}>
        {t("demandLegend")} <span aria-hidden="true">●</span> {t("demandEventLegend")}
      </p>
    </section>
  );
}
