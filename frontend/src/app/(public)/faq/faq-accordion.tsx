"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const faqs = [
  {
    q: "¿Qué formatos de plano aceptan?",
    a: "Aceptamos PDF, PNG, JPG y TIFF. Los planos deben tener una resolución mínima de 300 DPI para mejores resultados.",
  },
  {
    q: "¿Qué formatos de salida genera?",
    a: "Generamos DXF compatible con AutoCAD, LibreCAD y la mayoría de software CAD. Los planes Pro y Business también incluyen DWG.",
  },
  {
    q: "¿Qué precisión tiene la detección?",
    a: "Nuestro sistema de detección tiene una precisión del 98% en muros, puertas y ventanas en planos bien definidos. Recomendamos revisar y ajustar manualmente.",
  },
  {
    q: "¿Puedo cancelar mi suscripción?",
    a: "Sí, podés cancelar en cualquier momento desde tu panel de facturación. El acceso continúa hasta el final del período facturado.",
  },
  {
    q: "¿Mis datos están seguros?",
    a: "Sí. Todos los planos se procesan con encriptación de extremo a extremo. No compartimos tus datos con terceros.",
  },
  {
    q: "¿Ofrecen planes para empresas?",
    a: "Sí, nuestro plan Business incluye API dedicada, soporte 24/7 y conversiones ilimitadas. Contactanos para más información.",
  },
];

export function FaqAccordion() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <div className="space-y-2">
      {faqs.map((faq, i) => (
        <div key={i} className="rounded-lg border">
          <button
            onClick={() => setOpen(open === i ? null : i)}
            className="flex w-full items-center justify-between px-4 py-3 text-left font-medium"
          >
            {faq.q}
            <ChevronDown className={cn("h-4 w-4 transition-transform", open === i && "rotate-180")} />
          </button>
          {open === i && (
            <div className="border-t px-4 py-3 text-sm text-muted-foreground">{faq.a}</div>
          )}
        </div>
      ))}
    </div>
  );
}
