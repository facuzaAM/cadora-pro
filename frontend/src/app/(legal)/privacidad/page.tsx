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

        <div className="mt-8 space-y-8 text-sm leading-relaxed text-muted-foreground">
          <section>
            <h2 className="text-lg font-semibold text-foreground">1. Datos que recopilamos</h2>
            <div className="mt-2 space-y-2">
              <p><strong className="text-foreground">Datos de cuenta:</strong> nombre, dirección de email y contraseña (hasheada) que proporcionás al registrarte. Si usás login con Google, recibimos tu nombre y email a través de OAuth.</p>
              <p><strong className="text-foreground">Planos arquitectónicos subidos:</strong> los archivos raster (PNG, JPG, TIFF) o PDF que cargás para conversión. Estos archivos se procesan para extraer elementos arquitectónicos y generar el archivo CAD resultante.</p>
              <p><strong className="text-foreground">Archivos generados:</strong> los archivos DXF y DWG que se producen a partir de tus planos.</p>
              <p><strong className="text-foreground">Datos de uso:</strong> información anónima sobre cómo interactuás con la plataforma (páginas visitadas, funciones utilizadas) con fines de mejora del producto.</p>
              <p><strong className="text-foreground">Datos de facturación:</strong> información de pago procesada por Paddle (nuestro procesador de pagos). No almacenamos datos de tarjetas de crédito en nuestros servidores.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">2. Retención de archivos</h2>
            <div className="mt-2 space-y-2">
              <p><strong className="text-foreground">Planos originales (PDF/IMG):</strong> se eliminan automáticamente a los 30 días de haber sido procesados. Una vez generado el resultado, el archivo original no es necesario y se borra por razones de privacidad y seguridad.</p>
              <p><strong className="text-foreground">Archivos generados (DXF/DWG):</strong> se mantienen disponibles mientras tu cuenta esté activa o hasta que los elimines manualmente.</p>
              <p><strong className="text-foreground">Al eliminarse una cuenta:</strong> todos los datos asociados (planos, archivos generados, historial) se eliminan de forma permanente en un plazo máximo de [PLAZO] días.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">3. Uso de planos para mejora del servicio</h2>
            <div className="mt-2">
              <p><strong className="text-foreground">Tus planos subidos NO se utilizan para entrenar ni mejorar el motor de detección automática.</strong> El pipeline de visión por computadora se entrena exclusivamente con datasets de uso interno y fuentes públicas con licencia. Los planos que subís se procesan únicamente para generar tu resultado y no se incorporan a ningún conjunto de datos de entrenamiento.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">4. Cómo usamos tus datos</h2>
            <div className="mt-2 space-y-2">
              <p>Utilizamos tus datos para:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Procesar tus conversiones de planos a CAD.</li>
                <li>Gestionar tu cuenta, suscripción y facturación.</li>
                <li>Enviarte comunicaciones relacionadas con tu cuenta (confirmaciones, alertas de uso, cambios en el servicio).</li>
                <li>Cumplir con obligaciones legales y regulatorias.</li>
                <li>Mejorar la experiencia general de la plataforma (datos de uso anónimos).</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">5. Con quién compartimos tus datos</h2>
            <div className="mt-2 space-y-2">
              <p>Compartimos información únicamente con los siguientes proveedores de infraestructura, que actúan como encargados del tratamiento:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li><strong className="text-foreground">Supabase:</strong> almacenamiento de archivos y base de datos.</li>
                <li><strong className="text-foreground">Paddle:</strong> procesamiento de pagos y facturación.</li>
                <li><strong className="text-foreground">[PROVEEDOR DE HOSTING]:</strong> alojamiento de la aplicación.</li>
              </ul>
              <p className="mt-2">No vendemos, alquilamos ni compartimos tus datos con terceros con fines de marketing o publicidad.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">6. Tus derechos</h2>
            <div className="mt-2 space-y-2">
              <p>De acuerdo con [JURISDICCIÓN], tenés derecho a:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li><strong className="text-foreground">Acceso:</strong> saber qué datos tuyos almacenamos.</li>
                <li><strong className="text-foreground">Rectificación:</strong> corregir datos inexactos o incompletos.</li>
                <li><strong className="text-foreground">Eliminación:</strong> solicitar la borrado permanente de tus datos.</li>
                <li><strong className="text-foreground">Portabilidad:</strong> recibir tus datos en un formato estructurado y de uso común.</li>
                <li><strong className="text-foreground">Oposición:</strong> oponerte al tratamiento de tus datos para ciertos fines.</li>
              </ul>
              <p className="mt-2">Podés ejercer estos derechos desde la sección de perfil de tu cuenta o contactándonos directamente.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">7. Seguridad</h2>
            <div className="mt-2">
              <p>Implementamos medidas técnicas y organizativas para proteger tus datos: encriptación en reposo y en tránsito (TLS), control de acceso restringido, y monitoreo continuo de la infraestructura. Ningún sistema es 100% seguro, pero trabajamos para mantener estándares de seguridad de la industria.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">8. Cookies</h2>
            <div className="mt-2">
              <p>Usamos cookies esenciales para la autenticación y funcionalidad del sitio. Para más detalles, consultá nuestra <Link href="/cookies" className="text-primary underline-offset-4 hover:underline">Política de Cookies</Link>.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">9. Cambios en esta política</h2>
            <div className="mt-2">
              <p>Podemos actualizar esta política periódicamente. Te notificaremos sobre cambios significativos por email o mediante un aviso en la plataforma.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">10. Contacto</h2>
            <div className="mt-2">
              <p>Para consultas sobre privacidad o para ejercer tus derechos: <a href="mailto:privacidad@cadora.pro" className="text-primary underline-offset-4 hover:underline">privacidad@cadora.pro</a>.</p>
              <p className="mt-1">[EMPRESA LEGAL] — [DIRECCIÓN] — [JURISDICCIÓN]</p>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
