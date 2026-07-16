"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Me, getMe } from "@/lib/api";

export default function Nav() {
  const t = useTranslations("nav");
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!sessionStorage.getItem("access_token")) return;
    getMe()
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  return (
    <nav
      style={{
        display: "flex",
        gap: "1.5rem",
        padding: "0.8rem 1.5rem",
        borderBottom: "1px solid #e0e0e0",
        background: "#fff",
      }}
    >
      <Link href="/">
        <strong>Aura</strong>
      </Link>
      {me !== null && (
        <>
          <Link href="/dashboard">{t("dashboard")}</Link>
          <Link href="/monitoring">{t("monitoring")}</Link>
          {/* Ustawienia (ceny, konto, zespół) tylko dla właściciela (§ role). */}
          {me.role === "owner" && <Link href="/settings">{t("settings")}</Link>}
        </>
      )}
    </nav>
  );
}
