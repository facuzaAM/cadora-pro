import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "@/providers/theme-provider";
import { Toaster } from "sonner";
import { AuthProvider } from "@/hooks/useAuth";
import { CookieConsent } from "@/components/features/landing/cookie-consent";
import { PageTransition } from "@/components/shared/page-transition";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://cadora.pro";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Cadora - De planos arquitectónicos a CAD",
    template: "%s - Cadora",
  },
  description:
    "Sube tu plano arquitectónico y obtén un archivo DXF/DWG editable con detección automática de muros, puertas, ventanas, habitaciones, textos y cotas.",
  keywords: [
    "planos arquitectónicos",
    "CAD",
    "DXF",
    "DWG",
    "detección automática",
    "muros",
    "puertas",
    "ventanas",
  ],
  authors: [{ name: "Cadora" }],
  creator: "Cadora",
  openGraph: {
    type: "website",
    locale: "es_AR",
    siteName: "Cadora",
    title: "Cadora - De planos arquitectónicos a CAD",
    description:
      "Sube tu plano arquitectónico y obtén un archivo DXF/DWG editable con detección automática de muros, puertas y ventanas.",
    url: siteUrl,
    images: [{ url: "/og-image.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Cadora - De planos arquitectónicos a CAD",
    description:
      "Sube tu plano arquitectónico y obtén un archivo DXF/DWG editable con detección automática.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AuthProvider>
            <PageTransition>{children}</PageTransition>
            <CookieConsent />
            <Toaster richColors closeButton position="bottom-right" />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
