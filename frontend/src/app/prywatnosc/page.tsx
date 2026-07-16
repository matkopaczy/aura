import Link from "next/link";
import { getTranslations } from "next-intl/server";

export default async function PrivacyPage() {
  const t = await getTranslations("privacy");
  return (
    <main>
      <h1>{t("title")}</h1>
      <p>{t("intro")}</p>
      <h2>{t("collectTitle")}</h2>
      <p>{t("collect")}</p>
      <h2>{t("icalTitle")}</h2>
      <p>{t("ical")}</p>
      <h2>{t("rightsTitle")}</h2>
      <p>{t("rights")}</p>
      <p>
        <Link href="/">{t("back")}</Link>
      </p>
    </main>
  );
}
