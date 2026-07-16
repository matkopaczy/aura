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
