"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  ApiError,
  EventItem,
  Market,
  curationBulk,
  curationCreate,
  curationList,
  curationRefresh,
  curationUpdate,
  getMarkets,
} from "@/lib/api";

const EMPTY_FORM = {
  name: "",
  category: "",
  district: "",
  start_date: "",
  end_date: "",
  impact_strength: "0.5",
};

export default function CurationPage() {
  const t = useTranslations("curation");
  const [markets, setMarkets] = useState<Market[]>([]);
  const [slug, setSlug] = useState("");
  const [events, setEvents] = useState<EventItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleError = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
      window.location.href = "/login";
      return;
    }
    setError(e instanceof ApiError && e.status === 403 ? "forbidden" : "loadError");
  }, []);

  const reload = useCallback(
    (marketSlug: string) => {
      curationList(marketSlug)
        .then((list) => {
          setEvents(list);
          setSelected(new Set()); // zaznaczenie dotyczyło poprzedniej listy
        })
        .catch(handleError);
    },
    [handleError],
  );

  useEffect(() => {
    getMarkets()
      .then((list) => {
        setMarkets(list);
        if (list.length > 0) setSlug(list[0].slug);
      })
      .catch(handleError);
  }, [handleError]);

  useEffect(() => {
    if (!slug) return;
    reload(slug);
  }, [slug, reload]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const drafts = events.filter((e) => e.curation_status === "draft");

  function selectAllDrafts() {
    setSelected(new Set(drafts.map((e) => e.id)));
  }

  async function setStatus(id: string, status: "approved" | "rejected") {
    try {
      await curationUpdate(id, { curation_status: status });
      reload(slug);
    } catch (e) {
      handleError(e);
    }
  }

  async function bulkDecide(status: "approved" | "rejected") {
    if (selected.size === 0) return;
    try {
      await curationBulk([...selected], status);
      reload(slug);
    } catch (e) {
      handleError(e);
    }
  }

  async function refreshSources() {
    setNotice(null);
    try {
      await curationRefresh();
      setNotice("refreshStarted");
    } catch (e) {
      handleError(e);
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await curationCreate({
        market_slug: slug,
        name: form.name,
        category: form.category,
        district: form.district || null,
        start_date: form.start_date,
        end_date: form.end_date,
        impact_strength: Number(form.impact_strength),
        source: "kurator",
      });
      setForm(EMPTY_FORM);
      reload(slug);
    } catch (e) {
      handleError(e);
    }
  }

  const statusLabel: Record<EventItem["curation_status"], string> = {
    draft: t("statusDraft"),
    approved: t("statusApproved"),
    rejected: t("statusRejected"),
  };

  return (
    <main style={{ maxWidth: 960 }}>
      <h1>{t("title")}</h1>

      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
        <select
          value={slug}
          onChange={(e) => {
            setError(null); // stary błąd nie dotyczy nowo wybranego rynku
            setSlug(e.target.value);
          }}
        >
          {markets.map((m) => (
            <option key={m.slug} value={m.slug}>
              {m.name}
            </option>
          ))}
        </select>
        <button type="button" onClick={refreshSources}>
          {t("refresh")}
        </button>
        <button type="button" onClick={() => reload(slug)}>
          {t("reloadList")}
        </button>
        <span>{t("draftsCount", { count: drafts.length })}</span>
      </div>

      {notice !== null && <p>{t(notice)}</p>}
      {error !== null && <p className="error">{t(error)}</p>}

      <div style={{ display: "flex", gap: "0.75rem", margin: "0.75rem 0", flexWrap: "wrap" }}>
        <button type="button" onClick={selectAllDrafts} disabled={drafts.length === 0}>
          {t("selectAllDrafts")}
        </button>
        <button type="button" onClick={() => setSelected(new Set())} disabled={selected.size === 0}>
          {t("clearSelection")}
        </button>
        <button type="button" onClick={() => bulkDecide("approved")} disabled={selected.size === 0}>
          {t("bulkApprove", { count: selected.size })}
        </button>
        <button type="button" onClick={() => bulkDecide("rejected")} disabled={selected.size === 0}>
          {t("bulkReject", { count: selected.size })}
        </button>
      </div>

      <table>
        <thead>
          <tr>
            <th></th>
            <th>{t("name")}</th>
            <th>{t("category")}</th>
            <th>{t("dates")}</th>
            <th>{t("impact")}</th>
            <th>{t("status")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>
                <input
                  type="checkbox"
                  aria-label={event.name}
                  checked={selected.has(event.id)}
                  onChange={() => toggle(event.id)}
                />
              </td>
              <td>{event.name}</td>
              <td>{event.category}</td>
              <td>
                {event.start_date} – {event.end_date}
              </td>
              <td>{event.impact_strength.toFixed(2)}</td>
              <td>{statusLabel[event.curation_status]}</td>
              <td>
                {event.curation_status !== "approved" && (
                  <button type="button" onClick={() => setStatus(event.id, "approved")}>
                    {t("approve")}
                  </button>
                )}{" "}
                {event.curation_status !== "rejected" && (
                  <button type="button" onClick={() => setStatus(event.id, "rejected")}>
                    {t("reject")}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>{t("addTitle")}</h2>
      <form onSubmit={handleSubmit}>
        <label htmlFor="name">{t("name")}</label>
        <input
          id="name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <label htmlFor="category">{t("category")}</label>
        <input
          id="category"
          value={form.category}
          onChange={(e) => setForm({ ...form, category: e.target.value })}
          required
        />
        <label htmlFor="district">{t("district")}</label>
        <input
          id="district"
          value={form.district}
          onChange={(e) => setForm({ ...form, district: e.target.value })}
        />
        <label htmlFor="start">{t("startDate")}</label>
        <input
          id="start"
          type="date"
          value={form.start_date}
          onChange={(e) => setForm({ ...form, start_date: e.target.value })}
          required
        />
        <label htmlFor="end">{t("endDate")}</label>
        <input
          id="end"
          type="date"
          value={form.end_date}
          onChange={(e) => setForm({ ...form, end_date: e.target.value })}
          required
        />
        <label htmlFor="impact">{t("impact")}</label>
        <input
          id="impact"
          type="number"
          min="0"
          max="1"
          step="0.05"
          value={form.impact_strength}
          onChange={(e) => setForm({ ...form, impact_strength: e.target.value })}
          required
        />
        <button type="submit">{t("submit")}</button>
      </form>
    </main>
  );
}
