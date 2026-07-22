import type { Metadata } from "next";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { ContactForm } from "./contact-form";

export const metadata: Metadata = {
  title: "Contacto - Cadora",
  description: "Comunicate con el equipo de Cadora",
};

export default function ContactoPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />
      <main className="mx-auto flex w-full max-w-4xl flex-1 items-center justify-center px-4 py-12">
        <div className="grid w-full gap-12 md:grid-cols-2">
          <div>
            <h1 className="text-3xl font-bold">Contacto</h1>
            <p className="mt-2 text-muted-foreground">Estamos acá para ayudarte. Respondemos en menos de 24 horas.</p>
            <div className="mt-8 space-y-4 text-sm">
              <div>
                <p className="font-medium">Soporte técnico</p>
                <p className="text-muted-foreground"><a href="mailto:soporte@cadora.pro" className="hover:text-foreground">soporte@cadora.pro</a></p>
              </div>
              <div>
                <p className="font-medium">Ventas</p>
                <p className="text-muted-foreground"><a href="mailto:ventas@cadora.pro" className="hover:text-foreground">ventas@cadora.pro</a></p>
              </div>
              <div>
                <p className="font-medium">Privacidad</p>
                <p className="text-muted-foreground"><a href="mailto:privacidad@cadora.pro" className="hover:text-foreground">privacidad@cadora.pro</a></p>
              </div>
            </div>
          </div>
          <ContactForm />
        </div>
      </main>
    </div>
  );
}
