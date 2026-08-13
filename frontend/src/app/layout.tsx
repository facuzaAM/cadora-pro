import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "@/providers/theme-provider";
import { Toaster } from "sonner";
import { AuthProvider } from "@/hooks/useAuth";
import { GoogleAnalytics } from "@/components/shared/google-analytics";
import { CookieConsent } from "@/components/features/landing/cookie-consent";
import { PageTransition } from "@/components/shared/page-transition";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://cadora.pro";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Convierte PDF, PNG, JPG, JPEG y TIFF a CAD | Cadora",
    template: "%s - Cadora",
  },
  description:
    "Convierte planos arquitectónicos en PDF, PNG, JPG, JPEG o TIFF — incluso generados con IA — a archivos DXF/DWG editables con detección automática de muros, puertas, ventanas, habitaciones, textos y cotas.",
  keywords: [
    "convertir pdf a dxf",
    "convertir pdf a cad",
    "convertir imagen a cad",
    "convertir plano a dwg",
    "plano generado por ia",
    "planos arquitectónicos",
    "vectorizar plano arquitectónico",
    "dxf",
    "dwg",
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
    title: "Convierte PDF, PNG, JPG, JPEG y TIFF a CAD | Cadora",
    description:
      "Sube tu plano arquitectónico en PDF, PNG, JPG, JPEG o TIFF — escaneado, fotografiado o generado con IA — y obtén un DXF/DWG editable con detección automática de muros, puertas y ventanas.",
    url: siteUrl,
    images: [{ url: "/og-image.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Convierte PDF, PNG, JPG, JPEG y TIFF a CAD | Cadora",
    description:
      "Convierte planos en PDF, PNG, JPG, JPEG o TIFF — incluso generados con IA — a DXF/DWG editables con detección automática.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
  },
  verification: {
    google: "Z9q4ZpBcmh46FqABObpCDy6Qt1SbLpk3OL1gF2tB0Eo",
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
            <GoogleAnalytics />
            <CookieConsent />
            <Toaster richColors closeButton position="bottom-right" />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
