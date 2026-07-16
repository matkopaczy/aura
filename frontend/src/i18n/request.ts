import { getRequestConfig } from "next-intl/server";

// i18n od pierwszej linii kodu (§6.2 pkt 5): jedyny dziś język to pl,
// ale wszystkie teksty UI żyją w plikach tłumaczeń, nie w komponentach.
export default getRequestConfig(async () => {
  const locale = "pl";
  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
