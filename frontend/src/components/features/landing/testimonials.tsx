"use client";

import { Quote, Star } from "lucide-react";

const testimonials = [
  {
    name: "Arq. Martín Gutiérrez",
    role: "Estudio de arquitectura independiente",
    text: "Antes pasaba horas digitalizando planos escaneados a mano. Con Cadora, subo el PDF y en minutos tengo el DXF con muros, puertas y ventanas detectados. La precisión me ahorra al menos 2 horas por proyecto.",
    rating: 5,
  },
  {
    name: "Ing. Laura Fernández",
    role: "Constructora del Sur S.A.",
    text: "Evaluamos varias herramientas de conversión. Cadora fue la única que detectó correctamente las ventanas en un plano generado con IA. El resto las omitía o las marcaba como puertas.",
    rating: 5,
  },
  {
    name: "Carlos Méndez",
    role: "Diseñador de interiores",
    text: "La función de detección de ambientes y el OCR me permite mantener los nombres de las habitaciones y las cotas originales del plano. El tiempo de edición posterior se redujo un 70%.",
    rating: 4,
  },
];

export function Testimonials() {
  return (
    <section className="py-16 lg:py-24">
      <div className="mx-auto max-w-6xl px-4 text-center">
        <h2 className="text-3xl font-bold tracking-tight">Lo que dicen nuestros usuarios</h2>
        <p className="mt-2 text-muted-foreground">
          Arquitectos e ingenieros que ya confían en Cadora para su flujo de trabajo.
        </p>

        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {testimonials.map((t) => (
            <div
              key={t.name}
              className="relative flex flex-col rounded-xl border bg-card p-6 text-left"
            >
              <Quote className="mb-2 h-6 w-6 text-primary/40" />
              <p className="flex-1 text-sm text-muted-foreground">{t.text}</p>
              <div className="mt-4 flex items-center gap-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star
                    key={i}
                    className={`h-3.5 w-3.5 ${
                      i < t.rating
                        ? "fill-amber-400 text-amber-400"
                        : "text-muted-foreground/30"
                    }`}
                  />
                ))}
              </div>
              <p className="mt-2 text-sm font-medium">{t.name}</p>
              <p className="text-xs text-muted-foreground">{t.role}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
