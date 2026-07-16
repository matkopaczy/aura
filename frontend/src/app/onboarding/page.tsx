"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ApiError, ParsedListing, createProperty, parseListing } from "@/lib/api";

export default function OnboardingPage() {
  const t = useTranslations("onboarding");
  const [url, setUrl] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [parsed, setParsed] = useState<ParsedListing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    property_type: "apartment",
    capacity: "4",
    base_price: "",
    min_price: "",
    max_price: "",
    ical_url: "",
  });

  function handleError(e: unknown) {
    if (e instanceof ApiError && e.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (e instanceof ApiError && e.status === 422) setError("unsupportedUrl");
    else if (e instanceof ApiError && e.status === 404) setError("noMarket");
    else if (e instanceof ApiError && e.status === 503) setError("listingUnavailable");
    else setError("genericError");
  }

  async function analyze(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setAnalyzing(true);
    try {
      const result = await parseListing(url);
      setParsed(result);
      setForm((f) => ({
        ...f,
        name: result.name,
        base_price: result.proposed_base_price ?? "",
      }));
    } catch (e) {
      handleError(e);
    } finally {
      setAnalyzing(false);
    }
  }

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (parsed === null) return;
    setError(null);
    try {
      await createProperty({
        market_slug: parsed.market_slug,
        name: form.name,
        property_type: form.property_type,
        lat: parsed.lat,
        lng: parsed.lng,
        capacity: Number(form.capacity),
        base_price: form.base_price ? Number(form.base_price) : null,
        min_price: Number(form.min_price),
        max_price: form.max_price ? Number(form.max_price) : null,
        ical_url: form.ical_url || null,
      });
      window.location.href = "/dashboard";
    } catch (e) {
      handleError(e);
    }
  }

  return (
    <main>
      <h1>{t("title")}</h1>
      <form onSubmit={analyze}>
        <label htmlFor="url">{t("step1")}</label>
        <input
          id="url"
          type="url"
          value={url}
          placeholder={t("urlPlaceholder")}
          onChange={(e) => setUrl(e.target.value)}
          required
        />
        <button type="submit" disabled={analyzing}>
          {analyzing ? t("analyzing") : t("analyze")}
        </button>
      </form>

      {error !== null && <p className="error">{t(error)}</p>}

      {parsed !== null && (
        <form onSubmit={create}>
          <p>
            <strong>{t("detected", { name: parsed.name, market: parsed.market_name })}</strong>
          </p>
          <label htmlFor="name">{t("name")}</label>
          <input
            id="name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <label htmlFor="type">{t("propertyType")}</label>
          <select
            id="type"
            value={form.property_type}
            onChange={(e) => setForm({ ...form, property_type: e.target.value })}
          >
            <option value="apartment">{t("typeApartment")}</option>
            <option value="guesthouse">{t("typeGuesthouse")}</option>
            <option value="room">{t("typeRoom")}</option>
          </select>
          <label htmlFor="capacity">{t("capacity")}</label>
          <input
            id="capacity"
            type="number"
            min="1"
            max="50"
            value={form.capacity}
            onChange={(e) => setForm({ ...form, capacity: e.target.value })}
            required
          />
          <label htmlFor="base">
            {t("basePrice")} — {t("proposedBase")}: {parsed.proposed_base_price ?? "—"}
          </label>
          <input
            id="base"
            type="number"
            min="1"
            value={form.base_price}
            onChange={(e) => setForm({ ...form, base_price: e.target.value })}
            required
          />
          <label htmlFor="min">{t("minPrice")}</label>
          <input
            id="min"
            type="number"
            min="1"
            value={form.min_price}
            onChange={(e) => setForm({ ...form, min_price: e.target.value })}
            required
          />
          <label htmlFor="max">{t("maxPrice")}</label>
          <input
            id="max"
            type="number"
            min="1"
            value={form.max_price}
            onChange={(e) => setForm({ ...form, max_price: e.target.value })}
          />
          <label htmlFor="ical">{t("icalUrl")}</label>
          <input
            id="ical"
            type="url"
            value={form.ical_url}
            onChange={(e) => setForm({ ...form, ical_url: e.target.value })}
          />
          <button type="submit">{t("create")}</button>
        </form>
      )}
    </main>
  );
}
