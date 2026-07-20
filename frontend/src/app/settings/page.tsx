"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ApiError, Me, Property, getMe, getProperties, updateProperty } from "@/lib/api";
import AccountSection from "@/components/AccountSection";
import BookingImportSection from "@/components/BookingImportSection";
import TeamSection from "@/components/TeamSection";

function formFromProperty(p: Property) {
  return {
    name: p.name,
    base_price: p.base_price ?? "",
    min_price: p.min_price,
    max_price: p.max_price ?? "",
    ical_url: p.ical_url ?? "",
  };
}

export default function SettingsPage() {
  const t = useTranslations("settings");
  const to = useTranslations("onboarding");
  const tRoot = useTranslations();
  const [me, setMe] = useState<Me | null>(null);
  const [properties, setProperties] = useState<Property[]>([]);
  const [propertyId, setPropertyId] = useState("");
  const [form, setForm] = useState({
    name: "",
    base_price: "",
    min_price: "",
    max_price: "",
    ical_url: "",
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((e: unknown, key: string) => {
    if (e instanceof ApiError && e.status === 401) {
      window.location.href = "/login";
      return;
    }
    setError(key);
  }, []);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((e) => handleError(e, "loadError"));
  }, [handleError]);

  useEffect(() => {
    if (me?.role !== "owner") return; // recepcja nie ładuje ustawień właściciela
    getProperties()
      .then((list) => {
        setProperties(list);
        if (list.length > 0) {
          setPropertyId(list[0].id);
          setForm(formFromProperty(list[0]));
        }
      })
      .catch((e) => handleError(e, "loadError"));
  }, [me, handleError]);

  function selectProperty(id: string) {
    setPropertyId(id);
    const prop = properties.find((p) => p.id === id);
    if (prop) setForm(formFromProperty(prop));
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const updated = await updateProperty(propertyId, {
        name: form.name,
        base_price: form.base_price ? Number(form.base_price) : null,
        min_price: Number(form.min_price),
        max_price: form.max_price ? Number(form.max_price) : null,
        ical_url: form.ical_url || null,
      });
      setProperties((list) => list.map((p) => (p.id === updated.id ? updated : p)));
      setForm(formFromProperty(updated)); // wartości znormalizowane przez backend
      setMessage("saved");
    } catch (e) {
      handleError(e, "saveError");
    }
  }

  if (me !== null && me.role !== "owner") {
    return (
      <main>
        <h1>{t("title")}</h1>
        <p>{tRoot("ownerOnly")}</p>
      </main>
    );
  }

  return (
    <main>
      <h1>{t("title")}</h1>
      {properties.length > 1 && (
        <select value={propertyId} onChange={(e) => selectProperty(e.target.value)}>
          {properties.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      )}
      {error !== null && <p className="error">{t(error)}</p>}
      {message !== null && <p>{t(message)}</p>}
      {propertyId && (
        <form onSubmit={save}>
          <label htmlFor="name">{to("name")}</label>
          <input
            id="name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <label htmlFor="base">{to("basePrice")}</label>
          <input
            id="base"
            type="number"
            min="1"
            value={form.base_price}
            onChange={(e) => setForm({ ...form, base_price: e.target.value })}
          />
          <label htmlFor="min">{to("minPrice")}</label>
          <input
            id="min"
            type="number"
            min="1"
            value={form.min_price}
            onChange={(e) => setForm({ ...form, min_price: e.target.value })}
            required
          />
          <label htmlFor="max">{to("maxPrice")}</label>
          <input
            id="max"
            type="number"
            min="1"
            value={form.max_price}
            onChange={(e) => setForm({ ...form, max_price: e.target.value })}
          />
          <label htmlFor="ical">{to("icalUrl")}</label>
          <input
            id="ical"
            type="url"
            value={form.ical_url}
            onChange={(e) => setForm({ ...form, ical_url: e.target.value })}
          />
          <button type="submit">{t("save")}</button>
        </form>
      )}
      {propertyId && <BookingImportSection propertyId={propertyId} />}
      <TeamSection />
      <AccountSection />
    </main>
  );
}
