"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { deleteAccount, exportAccount } from "@/lib/api";

export default function AccountSection() {
  const t = useTranslations("account");
  const [confirming, setConfirming] = useState(false);
  const [confirmWord, setConfirmWord] = useState("");

  async function doExport() {
    const data = await exportAccount();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "aura-moje-dane.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function doDelete() {
    await deleteAccount();
    sessionStorage.removeItem("access_token");
    window.location.href = "/";
  }

  return (
    <section style={{ marginTop: "3rem", borderTop: "1px solid #e0e0e0", paddingTop: "1.5rem" }}>
      <h2>{t("title")}</h2>
      <button type="button" onClick={doExport}>
        {t("export")}
      </button>
      <p>
        <Link href="/prywatnosc">{t("privacyLink")}</Link>
      </p>

      <h3>{t("deleteTitle")}</h3>
      <p className="error">{t("deleteWarning")}</p>
      {!confirming ? (
        <button type="button" onClick={() => setConfirming(true)}>
          {t("delete")}
        </button>
      ) : (
        <div>
          <label htmlFor="confirm">{t("deleteConfirm")}</label>
          <input
            id="confirm"
            value={confirmWord}
            onChange={(e) => setConfirmWord(e.target.value)}
          />
          <button
            type="button"
            disabled={confirmWord !== t("deleteConfirmWord")}
            onClick={doDelete}
          >
            {t("delete")}
          </button>
        </div>
      )}
    </section>
  );
}
