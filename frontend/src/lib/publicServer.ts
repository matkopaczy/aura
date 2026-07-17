// Serwerowy odczyt danych publicznych do stron SEO (§5.2).
// Osobno od lib/api.ts (klient) — tu SSR + ISR (odświeżanie co godzinę),
// dane w HTML od razu dla crawlerów.
import { MarketPreview, PublicMarket } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REVALIDATE_SECONDS = 3600;

export async function fetchPublicMarkets(): Promise<PublicMarket[]> {
  const res = await fetch(`${API_URL}/api/public/markets`, {
    next: { revalidate: REVALIDATE_SECONDS },
  });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchMarketPreview(slug: string): Promise<MarketPreview | null> {
  const res = await fetch(`${API_URL}/api/public/preview/${slug}?days=30`, {
    next: { revalidate: REVALIDATE_SECONDS },
  });
  if (!res.ok) return null;
  return res.json();
}

export function averageMedian(preview: MarketPreview): number | null {
  const values = preview.days
    .map((d) => (d.median_price ? Number(d.median_price) : null))
    .filter((v): v is number => v !== null);
  if (values.length === 0) return null;
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
}

export function averageOccupancy(preview: MarketPreview): number | null {
  const values = preview.days
    .map((d) => d.occupancy)
    .filter((v): v is number => v !== null);
  if (values.length === 0) return null;
  return Math.round((values.reduce((a, b) => a + b, 0) / values.length) * 100);
}
