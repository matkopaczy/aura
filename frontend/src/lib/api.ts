const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token =
    typeof window !== "undefined" ? sessionStorage.getItem("access_token") : null;
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "unknown_error" }));
    throw new ApiError(response.status, body.detail ?? "unknown_error");
  }
  return response.json() as Promise<T>;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export interface Market {
  slug: string;
  name: string;
  currency_code: string;
  coverage_level: "monitoring" | "recommendations";
}

export interface MonitoringDay {
  stay_date: string;
  median_price: string | null;
  sample_size: number;
  occupancy: number | null;
  price_position: number | null;
}

export interface MonitoringResponse {
  market_slug: string;
  currency_code: string;
  days: MonitoringDay[];
}

export interface EventItem {
  id: string;
  market_slug: string;
  name: string;
  category: string;
  district: string | null;
  start_date: string;
  end_date: string;
  impact_strength: number;
  source: string;
  curation_status: "draft" | "approved" | "rejected";
}

export const getMarkets = () => request<Market[]>("/api/markets");

export const getMarketMonitoring = (slug: string, days = 30) =>
  request<MonitoringResponse>(`/api/monitoring/market/${slug}?days=${days}`);

export const getMarketEvents = (slug: string) =>
  request<EventItem[]>(`/api/events/${slug}`);

export const curationList = (slug: string) =>
  request<EventItem[]>(`/api/curation/events/${slug}`);

export const curationUpdate = (id: string, patch: Partial<EventItem>) =>
  request<EventItem>(`/api/curation/events/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });

export interface EventCreate {
  market_slug: string;
  name: string;
  category: string;
  district?: string | null;
  start_date: string;
  end_date: string;
  impact_strength: number;
  source: string;
}

export const curationCreate = (body: EventCreate) =>
  request<EventItem>("/api/curation/events", {
    method: "POST",
    body: JSON.stringify(body),
  });

export interface Property {
  id: string;
  market_slug: string;
  name: string;
  property_type: string;
  capacity: number;
  currency_code: string;
  base_price: string | null;
  min_price: string;
  max_price: string | null;
  ical_url: string | null;
}

export const getProperties = () => request<Property[]>("/api/properties");

export const createProperty = (body: object) =>
  request<Property>("/api/properties", { method: "POST", body: JSON.stringify(body) });

export const updateProperty = (id: string, patch: object) =>
  request<Property>(`/api/properties/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });

export const getPropertyMonitoring = (id: string, days = 60) =>
  request<MonitoringResponse>(`/api/monitoring/property/${id}?days=${days}`);

export interface ExplanationFactor {
  key: string;
  pct: number;
  name?: string;
  impact?: number;
  occupancy?: number;
  position?: number;
}

export interface Recommendation {
  id: string;
  property_id: string;
  stay_date: string;
  recommended_price: string;
  previous_price: string | null;
  currency_code: string;
  status: "pending" | "accepted" | "rejected" | "expired";
  explanation_template_key: string;
  explanation_params: { factors: ExplanationFactor[]; median: string | null };
  decided_at: string | null;
}

export const getRecommendations = (propertyId: string) =>
  request<Recommendation[]>(`/api/recommendations/${propertyId}`);

export const generateRecommendations = (propertyId: string, days = 60) =>
  request<Recommendation[]>(`/api/recommendations/${propertyId}/generate?days=${days}`, {
    method: "POST",
  });

export const decideRecommendation = (id: string, decision: "accepted" | "rejected") =>
  request<Recommendation>(`/api/recommendations/decision/${id}`, {
    method: "POST",
    body: JSON.stringify({ decision }),
  });

export interface Attribution {
  accepted_count: number;
  sold_count: number;
  extra_revenue: string;
  currency_code: string;
}

export const getAttribution = (propertyId: string) =>
  request<Attribution>(`/api/recommendations/attribution/${propertyId}`);

export interface ParsedListing {
  name: string;
  lat: number;
  lng: number;
  market_slug: string;
  market_name: string;
  currency_code: string;
  proposed_base_price: string | null;
}

export const parseListing = (url: string) =>
  request<ParsedListing>("/api/onboarding/parse", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
