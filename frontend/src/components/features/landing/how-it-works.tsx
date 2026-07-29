import { Upload, Cog, Download } from "lucide-react";

const steps = [
  {
    icon: Upload,
    step: "1",
    title: "Sube el plano",
    desc: "Arrastra tu PDF o imagen. Soporta PNG, JPG, TIFF y PDF.",
  },
  {
    icon: Cog,
    step: "2",
    title: "Procesamiento automático",
    desc: "Nuestro motor de detección analiza y detecta cada elemento arquitectónico.",
  },
  {
    icon: Download,
    step: "3",
    title: "Exporta a CAD",
    desc: "Descarga DXF editable con capas organizadas. DWG disponible en planes Pro y Business.",
  },
] as const;

export function HowItWorks() {
  return (
    <section className="relative overflow-hidden py-16 lg:py-24">
      <div className="absolute inset-0 bg-grid-pattern-subtle pointer-events-none" />
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <h2 className="text-3xl font-bold tracking-tight">Cómo funciona</h2>
          <p className="mt-2 text-muted-foreground">
            Tres pasos simples para convertir tu plano en un archivo CAD profesional.
          </p>
        </div>
        <div className="mt-12 grid gap-8 sm:grid-cols-3">
          {steps.map((s, i) => (
            <div key={s.step} className="relative flex flex-col items-center text-center">
              <div className="relative">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-primary to-blue-600 text-2xl font-bold text-primary-foreground shadow-lg shadow-primary/25">
                  {s.step}
                </div>
                {i < steps.length - 1 && (
                  <div className="absolute left-full top-1/2 hidden h-[2px] w-[calc(100%-4rem)] -translate-y-1/2 bg-gradient-to-r from-primary/60 via-primary/20 to-transparent sm:block" />
                )}
              </div>
              <div className="mt-6 flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary/10 to-primary/5">
                <s.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-3 font-semibold">{s.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
