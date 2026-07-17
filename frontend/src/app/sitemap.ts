import type { MetadataRoute } from "next";
import { fetchPublicMarkets } from "@/lib/publicServer";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const markets = await fetchPublicMarkets();
  const reports = markets
    .filter((m) => m.coverage_level === "recommendations")
    .map((m) => ({
      url: `${SITE_URL}/rynek/${m.slug}`,
      changeFrequency: "daily" as const,
      priority: 0.8,
    }));
  return [
    { url: SITE_URL, changeFrequency: "weekly", priority: 1 },
    ...reports,
  ];
}
