"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { ApiError, confirmPasswordReset } from "@/lib/api";

function ResetPasswordForm() {
  const t = useTranslations("resetPassword");
  const token = useSearchParams().get("token");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setError(null);
    try {
      const result = await confirmPasswordReset(token, newPassword);
      sessionStorage.setItem("access_token", result.access_token);
      window.location.href = "/dashboard";
    } catch (e) {
      if (e instanceof ApiError && ["invalid", "expired", "used"].includes(e.detail)) {
        setError(t(e.detail as "invalid" | "expired" | "used"));
      } else {
        setError(t("genericError"));
      }
    }
  }

  if (!token) {
    return (
      <>
        <p className="error">{t("missingToken")}</p>
        <p>
          <a href="/forgot-password">{t("requestNewLink")}</a>
        </p>
      </>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="newPassword">{t("newPassword")}</label>
      <input
        id="newPassword"
        type="password"
        minLength={10}
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        required
      />
      {error !== null && (
        <>
          <p className="error">{error}</p>
          <p>
            <a href="/forgot-password">{t("requestNewLink")}</a>
          </p>
        </>
      )}
      <button type="submit">{t("submit")}</button>
    </form>
  );
}

export default function ResetPasswordPage() {
  const t = useTranslations("resetPassword");
  return (
    <main>
      <h1>{t("title")}</h1>
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </main>
  );
}
