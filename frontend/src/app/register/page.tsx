"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ApiError, register } from "@/lib/api";

export default function RegisterPage() {
  const t = useTranslations("register");
  const [accountName, setAccountName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const token = await register(accountName, email, password);
      sessionStorage.setItem("access_token", token.access_token);
      window.location.href = "/onboarding";
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 409 ? "emailTaken" : "genericError",
      );
    }
  }

  return (
    <main>
      <h1>{t("title")}</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="accountName">{t("accountName")}</label>
        <input
          id="accountName"
          value={accountName}
          onChange={(e) => setAccountName(e.target.value)}
          required
        />
        <label htmlFor="email">{t("email")}</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">{t("password")}</label>
        <input
          id="password"
          type="password"
          minLength={10}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error !== null && <p className="error">{t(error)}</p>}
        <button type="submit">{t("submit")}</button>
      </form>
      <p>
        <Link href="/login">{t("haveAccount")}</Link>
      </p>
    </main>
  );
}
