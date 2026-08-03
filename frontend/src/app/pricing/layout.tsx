import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Planes y Precios",
  description:
    "Elegí el plan de Cadora que mejor se adapte a tu estudio. Detección de ventanas en planos CAD con IA.",
};

export default function PricingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
