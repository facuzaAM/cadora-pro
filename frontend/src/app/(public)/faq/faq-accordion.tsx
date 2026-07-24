"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const faqs = [
  {
    q: "¿Cuánto tarda el procesamiento?",
    a: "El procesamiento normalmente toma entre 1 y 3 minutos, dependiendo del tamaño y la complejidad del plano. Planos simples con pocos elementos se procesan más rápido; planos grandes con muchos ambientes pueden tardar un poco más.",
  },
  {
    q: "¿Qué formatos de plano aceptan?",
    a: "Aceptamos PDF, PNG, JPG, JPEG y TIFF. Los planos deben tener una resolución mínima de 300 DPI para mejores resultados en la detección.",
  },
  {
    q: "¿Qué formatos de salida genera?",
    a: "Generamos DXF (compatible con AutoCAD, LibreCAD y la mayoría de software CAD). Los planes Pro y Business también incluyen exportación a DWG.",
  },
  {
    q: "¿Qué pasa si la detección no es precisa?",
    a: "La detección automática tiene alta precisión pero no es perfecta. Si algún elemento no se detectó correctamente, podés volver a procesar el plano desde tu dashboard. En una futura versión estarás able de editar los elementos detectados manualmente antes de exportar.",
  },
  {
    q: "¿Cuánto tiempo se conservan mis archivos?",
    a: "Los planos originales (PDF/IMG) se eliminan automáticamente a los 30 días de haber sido procesados. Los archivos generados (DXF/DWG) se mantienen mientras tu cuenta esté activa o hasta que los elimines manualmente desde tu dashboard.",
  },
  {
    q: "¿Puedo eliminar mis archivos antes?",
    a: "Sí. Podés eliminar proyectos y documentos individuales desde tu dashboard en cualquier momento. Al eliminar un proyecto se borran permanentemente el plano original y los archivos CAD generados.",
  },
  {
    q: "¿Puedo cancelar mi suscripción?",
    a: "Sí, podés cancelar en cualquier momento desde tu panel de facturación. Si es tu primer pago y pasás menos de 7 días, tenés derecho a reembolso total. Después de esos 7 días, la suscripción se mantiene activa hasta el fin del período pagado sin reembolso.",
  },
  {
    q: "¿Mis datos están seguros?",
    a: "Sí. Todos los planos se procesan con encriptación en reposo y en tránsito. Tus planos NO se utilizan para entrenar modelos de IA. No compartimos tus datos con terceros salvo los proveedores de infraestructura necesarios para operar el servicio.",
  },
  {
    q: "¿Ofrecen planes para empresas?",
    a: "Sí, nuestro plan Business incluye conversiones ilimitadas, 25 GB de almacenamiento, exportación DWG, procesamiento prioritario y soporte dedicado. Contactanos a ventas@cadora.pro para más información.",
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
