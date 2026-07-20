"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ApiError, BookingImportResult, importBookings } from "@/lib/api";

// Import CSV zrealizowanych rezerwacji (B) — pod prawdziwy ADR/RevPAR w panelu.
export default function BookingImportSection({ propertyId }: { propertyId: string }) {
  const t = useTranslations("bookingImport");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BookingImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const text = await file.text();
      setResult(await importBookings(propertyId, text));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "loadError");
    } finally {
      setBusy(false);
      e.target.value = ""; // pozwól wgrać ten sam plik ponownie
    }
  }

  return (
    <section style={{ marginTop: "2rem" }}>
      <h2>{t("title")}</h2>
      <p style={{ color: "#555" }}>{t("hint")}</p>
      <input type="file" accept=".csv,text/csv" onChange={onFile} disabled={busy} />
      {busy && <p>{t("busy")}</p>}
      {result !== null && (
        <p style={{ color: "#2f6b2f" }}>
          {t("done", {
            nights: result.imported_nights,
            reservations: result.reservations,
            skipped: result.skipped_rows,
          })}
        </p>
      )}
      {error !== null && <p className="error">{t(error)}</p>}
    </section>
  );
}
