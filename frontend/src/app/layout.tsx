import type { Metadata } from "next";
import Link from "next/link";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aura",
  description: "Dynamiczny pricing dla samodzielnych gospodarzy",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale = await getLocale();
  const messages = await getMessages();
  const t = await getTranslations("nav");
  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
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
            <Link href="/dashboard">{t("dashboard")}</Link>
            <Link href="/monitoring">{t("monitoring")}</Link>
            <Link href="/settings">{t("settings")}</Link>
          </nav>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
