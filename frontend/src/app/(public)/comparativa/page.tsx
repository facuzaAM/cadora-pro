import type { Metadata } from "next";
import Link from "next/link";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { SiteFooter } from "@/components/layout/site-footer";
import { PageHero } from "@/components/shared/page-hero";
import { StructuredData } from "@/components/shared/structured-data";

export const metadata: Metadata = {
  title: "Comparativa - Cadora vs alternativas de conversión CAD",
  description:
    "Compará Cadora con otras opciones: dibujo manual, Scan2CAD, AutoCAD Raster Design, y otros conversores online. Velocidad, precisión, precio y formatos.",
};

const competitors = [
  {
    name: "Cadora",
    tag: "Online, automático",
    price: "Gratis – $60/mes",
    speed: "1-3 min",
    precision: "Alta (ML + CV)",
    formats: "PDF, PNG, JPG, TIFF → DXF, DWG",
    detection: "Muros, puertas, ventanas, arcos, OCR, cotas",
    manualWork: "Mínima (revisión rápida)",
    learning: "Ninguno",
  },
  {
    name: "Dibujo manual desde cero",
    tag: "AutoCAD / Revit",
    price: "$200+/mes (licencia)",
    speed: "4-8 horas por plano",
    precision: "Total (hecho a mano)",
    formats: "Cualquier CAD",
    detection: "N/A (se dibuja todo)",
    manualWork: "Completa",
    learning: "Alto (AutoCAD avanzado)",
  },
  {
    name: "Scan2CAD",
    tag: "Software de escritorio",
    price: "$199 (licencia única) + actualizaciones",
    speed: "5-15 min (manual)",
    precision: "Media (vectorización básica)",
    formats: "PNG, BMP, TIFF → DXF",
    detection: "Solo líneas (sin clasificación)",
    manualWork: "Alta (corregir capas)",
    learning: "Medio",
  },
  {
    name: "AutoCAD Raster Design",
    tag: "Plugin de AutoCAD",
    price: "$1.690/año (incl. AutoCAD)",
    speed: "10-30 min por plano",
    precision: "Media-alta (herramientas manuales)",
    formats: "TIFF, JPG, PNG → DWG",
    detection: "Solo líneas (sin IA)",
    manualWork: "Alta (herramientas semiautomáticas)",
    learning: "Alto (AutoCAD + plugin)",
  },
  {
    name: "Conversores online genéricos",
    tag: "Varios sitios web",
    price: "Gratis – $10/mes",
    speed: "2-10 min",
    precision: "Baja (vectorización genérica)",
    formats: "PDF, PNG → DXF (básico)",
    detection: "Solo líneas, sin clasificar",
    manualWork: "Muy alta",
    learning: "Bajo",
  },
];

export default function ComparativaPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <StructuredData data={{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Comparativa de conversión CAD",
        description: "Comparativa entre Cadora y otras herramientas de conversión de planos a CAD.",
      }} />
      <LandingNav />
      <PageHero
        title="Cadora vs otras herramientas"
        subtitle="Compará velocidad, precisión, precio y facilidad de uso"
      />
      <main className="flex-1 py-16 lg:py-24">
        <div className="mx-auto max-w-6xl px-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="pb-3 pr-4 font-semibold">Característica</th>
                  {competitors.map((c) => (
                    <th key={c.name} className={`pb-3 px-3 font-semibold whitespace-nowrap ${c.name === "Cadora" ? "text-primary" : ""}`}>
                      {c.name}
                      <div className="text-xs font-normal text-muted-foreground">{c.tag}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { label: "Precio", key: "price" as const },
                  { label: "Tiempo por plano", key: "speed" as const },
                  { label: "Precisión", key: "precision" as const },
                  { label: "Formatos", key: "formats" as const },
                  { label: "Detección", key: "detection" as const },
                  { label: "Trabajo manual", key: "manualWork" as const },
                  { label: "Curva de aprendizaje", key: "learning" as const },
                ].map((row) => (
                  <tr key={row.label} className="border-b last:border-0">
                    <td className="py-3 pr-4 font-medium text-muted-foreground">{row.label}</td>
                    {competitors.map((c) => (
                      <td key={c.name} className={`py-3 px-3 ${c.name === "Cadora" ? "font-medium text-primary" : ""}`}>
                        {c[row.key]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-12 rounded-xl border bg-card p-8 text-center">
            <h2 className="text-xl font-semibold">Probá Cadora gratis</h2>
            <p className="mt-2 text-muted-foreground">
              Subí tu plano y obtené el DXF en minutos, sin instalar nada.
            </p>
            <div className="mt-4 flex justify-center gap-4">
              <Link
                href="/"
                className="inline-flex items-center justify-center rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Probar demo
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center justify-center rounded-lg border bg-background px-6 py-2.5 text-sm font-medium hover:bg-muted"
              >
                Ver planes
              </Link>
            </div>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
