import type { Metadata } from "next";
import Link from "next/link";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { FaqAccordion } from "./faq-accordion";

export const metadata: Metadata = {
  title: "FAQ - Cadora",
  description: "Preguntas frecuentes sobre Cadora",
};

export default function FaqPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold">Preguntas Frecuentes</h1>
        <p className="mt-2 text-muted-foreground">Todo lo que necesitás saber sobre Cadora</p>
        <div className="mt-8">
          <FaqAccordion />
        </div>
        <p className="mt-8 text-center text-sm text-muted-foreground">
          ¿No encontrás lo que buscás?{" "}
          <Link href="/contacto" className="text-primary underline-offset-4 hover:underline">Contactanos</Link>
        </p>
      </main>
    </div>
  );
}
