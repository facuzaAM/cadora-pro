import { Ruler, DoorOpen, ScanLine, TextSearch, Hash, BrickWall, Sparkles, type LucideIcon } from "lucide-react";

type Feature = {
  icon: LucideIcon;
  title: string;
  desc: string;
  highlight?: boolean;
};

const features: Feature[] = [
  {
    icon: BrickWall,
    title: "Detección de Muros",
    desc: "Identifica automáticamente muros y tabiques con su espesor y longitud.",
  },
  {
    icon: DoorOpen,
    title: "Puertas y Ventanas",
    desc: "Reconoce puertas, ventanas y su dirección de apertura.",
  },
  {
    icon: ScanLine,
    title: "Segmentación de Ambientes",
    desc: "Delimita cada habitación con su área y perímetro.",
  },
  {
    icon: TextSearch,
    title: "Reconocimiento de Texto",
    desc: "Extrae etiquetas, rótulos y anotaciones del plano.",
  },
  {
    icon: Hash,
    title: "Cotas y Dimensiones",
    desc: "Detecta líneas de cota con sus medidas exactas.",
  },
  {
    icon: Ruler,
    title: "Exportación CAD",
    desc: "Genera archivos DXF editable con capas organizadas. DWG disponible en planes Pro y Business.",
  },
  {
    icon: Sparkles,
    title: "Compatible con planos generados por IA",
    desc: "Procesamos también planos creados con herramientas de IA: los vectorizamos a DXF/DWG igual que los tradicionales, sin configuración extra.",
    highlight: true,
  },
];

export function FeaturesGrid() {
  return (
    <section className="relative isolate overflow-hidden py-16 lg:py-24 bg-section-alt">
      <div className="absolute inset-0 bg-grid-cad -z-10 pointer-events-none" />
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <h2 className="text-3xl font-bold tracking-tight">Todo lo que necesitas</h2>
          <p className="mt-2 text-muted-foreground">
            Detección precisa de muros, puertas, ventanas y más. Compatible con planos escaneados, fotografiados o generados por IA.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.title} className={"group relative overflow-hidden rounded-xl border bg-card p-6 transition-all duration-300 hover:shadow-lg hover:border-primary/50 hover:-translate-y-0.5" + (f.highlight ? " lg:col-span-3 border-primary/40 bg-gradient-to-br from-primary/10 via-card to-card" : "")}>
                <span className="pointer-events-none absolute left-2 top-2 h-1.5 w-1.5 rounded-full bg-primary opacity-0 transition-all duration-300 group-hover:opacity-100 group-hover:scale-125" />
                <span className="pointer-events-none absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary opacity-0 transition-all duration-300 group-hover:opacity-100 group-hover:scale-125" />
                <span className="pointer-events-none absolute bottom-2 left-2 h-1.5 w-1.5 rounded-full bg-primary opacity-0 transition-all duration-300 group-hover:opacity-100 group-hover:scale-125" />
                <span className="pointer-events-none absolute bottom-2 right-2 h-1.5 w-1.5 rounded-full bg-primary opacity-0 transition-all duration-300 group-hover:opacity-100 group-hover:scale-125" />
                <div className="absolute right-0 top-0 h-20 w-20 translate-x-6 -translate-y-6 rounded-full bg-primary/[0.04] transition-all duration-300 group-hover:scale-150" />
                <div className="relative">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 group-hover:from-primary/20 group-hover:to-primary/10 transition-all duration-300">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="mt-4 font-semibold">{f.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
