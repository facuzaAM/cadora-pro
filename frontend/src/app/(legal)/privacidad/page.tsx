import type { Metadata } from "next";
import Link from "next/link";
import { Logo } from "@/components/shared/logo";

export const metadata: Metadata = {
  title: "Política de Privacidad - Cadora",
  description: "Política de privacidad y tratamiento de datos de Cadora",
};

export default function PrivacidadPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-3xl items-center px-4">
          <Link href="/"><Logo /></Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold">Política de Privacidad</h1>
        <p className="mt-2 text-sm text-muted-foreground">Última actualización: Julio 2026</p>

        <div className="mt-8 space-y-6 text-sm leading-relaxed text-muted-foreground">
          <section>
            <h2 className="text-lg font-semibold text-foreground">1. Datos que recopilamos</h2>
            <p className="mt-2">Recopilamos tu nombre, email, y los planos arquitectónicos que subís para procesar. También recopilamos datos de uso anónimos para mejorar el servicio.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">2. Cómo usamos tus datos</h2>
            <p className="mt-2">Usamos tus datos para: procesar tus conversiones, mejorar nuestro sistema de detección, comunicarnos sobre tu cuenta, y cumplir con obligaciones legales y de facturación.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">3. Almacenamiento y seguridad</h2>
            <p className="mt-2">Tus datos se almacenan en servidores seguros con encriptación en reposo y en tránsito. Los planos se eliminan automáticamente según tu plan vigente.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">4. Tus derechos</h2>
            <p className="mt-2">Podés solicitar la descarga, modificación o eliminación de tus datos en cualquier momento desde tu perfil o contactándonos.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">5. Cookies</h2>
            <p className="mt-2">Usamos cookies esenciales para la autenticación y funcionalidad. Para más detalles, consultá nuestra <Link href="/cookies" className="text-primary underline-offset-4 hover:underline">Política de Cookies</Link>.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">6. Contacto</h2>
            <p className="mt-2">Para ejercer tus derechos de privacidad: <a href="mailto:privacidad@cadora.pro" className="text-primary underline-offset-4 hover:underline">privacidad@cadora.pro</a>.</p>
          </section>
        </div>
      </main>
    </div>
  );
}
