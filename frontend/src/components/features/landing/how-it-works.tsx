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
    <section className="py-16 lg:py-24 bg-muted/50">
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <h2 className="text-3xl font-bold tracking-tight">Cómo funciona</h2>
          <p className="mt-2 text-muted-foreground">
            Tres pasos simples para convertir tu plano en un archivo CAD profesional.
          </p>
        </div>
        <div className="mt-12 grid gap-8 sm:grid-cols-3">
          {steps.map((s) => (
            <div key={s.step} className="relative flex flex-col items-center text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-2xl font-bold text-primary-foreground">
                {s.step}
              </div>
              <div className="mt-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
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
