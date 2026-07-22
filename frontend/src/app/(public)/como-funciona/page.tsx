import type { Metadata } from "next";
import Link from "next/link";
import { Logo } from "@/components/shared/logo";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { Upload, Cog, Download, DoorOpen, BrickWall, ScanLine, TextSearch, Hash, Ruler } from "lucide-react";

export const metadata: Metadata = {
  title: "Cómo funciona - Cadora",
  description: "Descubrí cómo Cadora convierte tus planos arquitectónicos en archivos CAD editables en tres simples pasos.",
};

const steps = [
  {
    icon: Upload,
    step: "1",
    title: "Subí tu plano",
    description: "Arrastrá y soltá tu archivo PDF, PNG, JPG o TIFF. No hay límite de tamaño complejo — nuestro sistema acepta planos de cualquier escala y resolución.",
    details: [
      "Soporte para PDF, PNG, JPG, JPEG y TIFF",
      "Hasta 50 MB por archivo",
      "Cualquier escala: 1:50, 1:100, 1:200, etc.",
    ],
  },
  {
    icon: Cog,
    step: "2",
    title: "Detección automática",
    description: "Nuestro motor de procesamiento analiza tu plano y detecta automáticamente todos los elementos arquitectónicos.",
    details: [
      "Muros y tabiques con espesor y longitud",
      "Puertas con dirección de apertura",
      "Ventanas fijas, batientes y correderas",
      "Textos, cotas y medidas",
    ],
  },
  {
    icon: Download,
    step: "3",
    title: "Descargá CAD",
    description: "Obtené un archivo DXF listo para abrir en AutoCAD, LibreCAD o cualquier software CAD. Las capas están organizadas por tipo de elemento.",
    details: [
      "Formato DXF R2010 compatible",
      "Capas: Muros, Puertas, Ventanas, Textos, Cotas",
      "DWG disponible en planes Pro y Business",
    ],
  },
];

const features = [
  { icon: BrickWall, title: "Muros", desc: "Detecta muros y tabiques con su espesor y orientación automáticamente." },
  { icon: DoorOpen, title: "Puertas", desc: "Identifica puertas simples, dobles y correderas con su dirección de apertura." },
  { icon: ScanLine, title: "Ventanas", desc: "Reconoce ventanas fijas, batientes y correderas en cualquier posición." },
  { icon: TextSearch, title: "Textos", desc: "Extrae etiquetas, nombres de ambientes y anotaciones del plano." },
  { icon: Hash, title: "Cotas", desc: "Detecta líneas de cota y sus medidas exactas." },
  { icon: Ruler, title: "Capas organizadas", desc: "Todo exportado con capas separadas para fácil edición en CAD." },
];

export default function ComoFuncionaPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />
      <main className="flex-1">
        {/* Hero */}
        <section className="py-16 text-center lg:py-24">
          <div className="mx-auto max-w-3xl px-4">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Cómo funciona Cadora</h1>
            <p className="mt-4 text-lg text-muted-foreground">
              Convertí tus planos arquitectónicos en archivos CAD editables en tres simples pasos.
            </p>
          </div>
        </section>

        {/* Steps */}
        <section className="bg-muted/50 py-16 lg:py-24">
          <div className="mx-auto max-w-4xl px-4">
            <div className="space-y-16">
              {steps.map((s) => (
                <div key={s.step} className="flex flex-col items-center gap-8 md:flex-row md:items-start md:text-left">
                  <div className="flex flex-col items-center gap-3 md:shrink-0">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-2xl font-bold text-primary-foreground">
                      {s.step}
                    </div>
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                      <s.icon className="h-6 w-6 text-primary" />
                    </div>
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold">{s.title}</h2>
                    <p className="mt-2 text-muted-foreground">{s.description}</p>
                    <ul className="mt-4 space-y-2">
                      {s.details.map((d) => (
                        <li key={d} className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                          {d}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Detection features */}
        <section className="py-16 lg:py-24">
          <div className="mx-auto max-w-4xl px-4">
            <h2 className="text-center text-3xl font-bold tracking-tight">Qué detecta automáticamente</h2>
            <p className="mt-2 text-center text-muted-foreground">
              Nuestro motor de procesamiento reconoce los elementos principales de cualquier plano arquitectónico.
            </p>
            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((f) => (
                <div key={f.title} className="rounded-xl border bg-card p-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <f.icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="mt-4 font-semibold">{f.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 lg:py-24 bg-muted/50">
          <div className="mx-auto max-w-3xl px-4 text-center">
            <h2 className="text-3xl font-bold tracking-tight">¿Listo para empezar?</h2>
            <p className="mt-4 text-muted-foreground">
              Registrate gratis y convertí tu primer plano en minutos.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link
                href="/register"
                className="inline-flex h-12 items-center justify-center rounded-xl bg-primary px-8 text-base font-semibold text-primary-foreground shadow transition-colors hover:bg-primary/90"
              >
                Comenzar gratis
              </Link>
              <Link
                href="/pricing"
                className="inline-flex h-12 items-center justify-center rounded-xl border bg-background px-8 text-base font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                Ver Planes
              </Link>
            </div>
          </div>
        </section>
      </main>
      <footer className="border-t py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 sm:flex-row">
          <Logo />
          <p className="text-sm text-muted-foreground">
            &copy; 2026 Cadora. Todos los derechos reservados.
          </p>
        </div>
      </footer>
    </div>
  );
}
