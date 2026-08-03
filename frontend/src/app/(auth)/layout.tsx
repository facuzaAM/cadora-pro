import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Acceso a tu cuenta",
  description: "Iniciá sesión o creá tu cuenta en Cadora.",
  robots: { index: false, follow: false },
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
