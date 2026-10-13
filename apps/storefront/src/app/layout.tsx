import "./globals.css";
import "./marketplace.css";
import { headers } from "next/headers";
export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale =
    (await headers()).get("x-retail-locale") === "ar" ? "ar" : "en";
  return (
    <html lang={locale} dir={locale === "ar" ? "rtl" : "ltr"}>
      <body>
        <a className="skip-link" href="#main">
          {locale === "ar" ? "انتقل إلى المحتوى" : "Skip to content"}
        </a>
        {children}
      </body>
    </html>
  );
}
