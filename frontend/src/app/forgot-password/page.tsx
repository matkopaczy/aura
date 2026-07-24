"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { requestPasswordReset } from "@/lib/api";

export default function ForgotPasswordPage() {
  const t = useTranslations("forgotPassword");
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await requestPasswordReset(email);
      setSent(true); // zawsze ta sama ścieżka — backend nigdy nie zdradza, czy konto istnieje
    } catch {
      setError(t("genericError"));
    }
  }

  return (
    <main>
      <h1>{t("title")}</h1>
      {sent ? (
        <p>{t("sent")}</p>
      ) : (
        <form onSubmit={handleSubmit}>
          <p>{t("hint")}</p>
          <label htmlFor="email">{t("email")}</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          {error !== null && <p className="error">{error}</p>}
          <button type="submit">{t("submit")}</button>
        </form>
      )}
      <p>
        <a href="/login">{t("backToLogin")}</a>
      </p>
    </main>
  );
}
