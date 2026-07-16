"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Subscription, getSubscription } from "@/lib/api";

export default function SubscriptionBanner() {
  const t = useTranslations("billing");
  const [sub, setSub] = useState<Subscription | null>(null);

  useEffect(() => {
    getSubscription()
      .then(setSub)
      .catch(() => setSub(null));
  }, []);

  if (sub === null) return null;

  let message: string;
  if (sub.is_expired) message = t("trialExpired");
  else if (sub.status === "trialing")
    message = t("trialBanner", { days: sub.trial_days_left ?? 0 });
  else if (sub.status === "active") message = t("active");
  else if (sub.status === "canceled") message = t("canceled");
  else message = t("active");

  const urgent = sub.is_expired || sub.status === "canceled";
  return (
    <div
      style={{
        padding: "0.6rem 1rem",
        borderRadius: 6,
        marginBottom: "1rem",
        background: urgent ? "#fbe9e7" : "#eef4ff",
        border: `1px solid ${urgent ? "#e0b4ac" : "#b8ccf0"}`,
      }}
    >
      {message}
      {sub.status === "trialing" && (
        <span>
          {" "}
          — {t("price", { price: Number(sub.price_per_property).toFixed(0), currency: sub.currency_code })}
        </span>
      )}
    </div>
  );
}
