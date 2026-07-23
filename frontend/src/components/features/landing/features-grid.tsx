import { Ruler, DoorOpen, ScanLine, TextSearch, Hash, BrickWall } from "lucide-react";

const features = [
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
] as const;

export function FeaturesGrid() {
  return (
    <section className="py-16 lg:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <h2 className="text-3xl font-bold tracking-tight">Todo lo que necesitas</h2>
          <p className="mt-2 text-muted-foreground">
            Detección precisa de muros, puertas, ventanas y más.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.title} className="group rounded-xl border bg-card p-6 transition-colors hover:border-primary/50">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="mt-4 font-semibold">{f.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
