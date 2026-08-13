import type { Metadata } from "next";
import Link from "next/link";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { SiteFooter } from "@/components/layout/site-footer";
import { PageHero } from "@/components/shared/page-hero";
import {
  Cpu,
  ScanLine,
  BrickWall,
  DoorOpen,
  Ruler,
  TextSearch,
  BrainCircuit,
  Cog,
} from "lucide-react";
import { StructuredData } from "@/components/shared/structured-data";

export const metadata: Metadata = {
  title: "Tecnología de detección - Cadora",
  description:
    "Cadora usa visión computacional avanzada (OpenCV) combinada con OCR para detectar automáticamente muros, puertas, ventanas, textos y cotas en planos arquitectónicos escaneados, generados por IA o exportados desde cualquier software CAD.",
  keywords: [
    "visión computacional planos",
    "detección automática muros",
    "ocr planos arquitectónicos",
    "convertir plano escaneado a cad",
    "ia para arquitectura",
    "procesamiento de imágenes planos",
  ],
};

const features = [
  {
    icon: ScanLine,
    title: "Preprocesamiento adaptativo",
    description:
      "El motor analiza el contraste y la nitidez de la imagen para elegir entre binarización Otsu (para planos nítidos) o umbral adaptativo (para planos con sombras, fotos o generados por IA). Un paso de CLAHE ecualiza el contraste y un denoising preserva bordes.",
  },
  {
    icon: BrickWall,
    title: "Detección de muros con Hough probabilístico",
    description:
      "Usamos la transformada de Hough probabilística con dos pasadas de parámetros: la primera captura muros largos y la segunda recupera segmentos cortos. Un agrupado colineal por union-find fusiona fragmentos del mismo muro, incluso cuando hay texto o mobiliario entre medio.",
  },
  {
    icon: DoorOpen,
    title: "Detección de puertas y ventanas",
    description:
      "Buscamos hojas ortogonales (líneas perpendiculares a los muros) y escaneamos el hueco de luz en la pared. Un arco de apertura detectado por muestreo de pixeles confirma el tipo de puerta. Para ventanas, identificamos los vidrios como líneas paralelas delgadas dentro del vano.",
  },
  {
    icon: Cog,
    title: "Refinamiento geométrico y curvas",
    description:
      "Los muros detectados se refinan eliminando trazos que pertenecen a hojas de puertas, arcos de apertura o líneas de vidrio. Los muros curvos se reconstruyen mediante RANSAC sobre los endpoints de las cuerdas, generando arcos perfectos que se exportan como entidades ARC en el DXF.",
  },
  {
    icon: Cpu,
    title: "Filtros de mobiliario y escaleras",
    description:
      "El motor distingue muros reales de mobiliario (camas, mesas, columnas) mediante detección de contornos cerrados. Las escaleras se identifican como grupos de líneas paralelas equidistantes y se excluyen de la salida CAD.",
  },
  {
    icon: Ruler,
    title: "Escala y metros reales",
    description:
      "La escala se extrae del OCR (formato 1:50, 1:100, ESC 1:50) y se convierte a metros usando la resolución real de rasterización (200 DPI). Las dimensiones finales están en metros en el archivo DXF o DWG.",
  },
  {
    icon: TextSearch,
    title: "OCR contextual",
    description:
      "Tesseract OCR con idioma español reconoce textos, nombres de ambientes, cotas y escalas. Un clasificador separa automáticamente nombres de habitaciones, notas generales y medidas dimensionales.",
  },
  {
    icon: BrainCircuit,
    title: "Pipeline completo en servidor dedicado",
    description:
      "La detección corre en un worker dedicado (contenedor separado de la API HTTP) con claim atómico sobre la base de datos, heartbeat y recuperación de trabajos estancados. Soporta múltiples páginas por proyecto con fusión de resultados.",
  },
];

export default function TecnologiaPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <StructuredData data={{
        "@context": "https://schema.org",
        "@type": "Article",
        headline: "Tecnología de detección de Cadora",
        description: "Cómo funciona el motor de visión computacional que convierte planos arquitectónicos a CAD.",
        publisher: { "@type": "Organization", name: "Cadora" },
      }} />
      <LandingNav />
      <PageHero
        title="Tecnología del motor de detección"
        subtitle="Visión computacional + OCR sobre planos arquitectónicos escaneados, fotografiados o generados con IA"
      />
      <main className="flex-1 py-16 lg:py-24">
        <div className="mx-auto max-w-4xl px-4">
          <div className="prose dark:prose-invert max-w-none mb-12">
            <p>
              Cadora combina técnicas clásicas de visión computacional (transformada de Hough,
              umbral adaptativo, CLAHE, RANSAC) con OCR (Tesseract) para convertir planos
              arquitectónicos en modelos CAD editables. El pipeline completo procesa desde
              la imagen original hasta el archivo DXF listo para descargar.
            </p>
          </div>
          <div className="space-y-10">
            {features.map((f) => (
              <div key={f.title} className="flex gap-4">
                <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <f.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">{f.title}</h2>
                  <p className="mt-1 text-muted-foreground">{f.description}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-16 rounded-xl border bg-card p-8 text-center">
            <h2 className="text-xl font-semibold">Probá el motor ahora</h2>
            <p className="mt-2 text-muted-foreground">
              Subí tu plano arquitectónico y obtené el DXF en segundos, sin registrarte.
            </p>
            <Link
              href="/"
              className="mt-4 inline-flex items-center justify-center rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Probar demo gratuita
            </Link>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
