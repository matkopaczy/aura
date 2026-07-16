"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ApiError, login } from "@/lib/api";

export default function LoginPage() {
  const t = useTranslations("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const token = await login(email, password);
      sessionStorage.setItem("access_token", token.access_token);
      window.location.href = "/";
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? t("invalidCredentials") : t("genericError"));
    }
  }

  return (
    <main>
      <h1>{t("title")}</h1>
      <form onSubmit={handleSubmit}>
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
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error !== null && <p className="error">{error}</p>}
        <button type="submit">{t("submit")}</button>
      </form>
    </main>
  );
}
