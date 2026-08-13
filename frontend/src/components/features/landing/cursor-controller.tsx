"use client";

import { usePathname } from "next/navigation";
import { CadCursor } from "@/components/features/landing/cad-cursor";

const PUBLIC_PATHS = [
  "/", "/como-funciona", "/tecnologia", "/comparativa",
  "/pricing", "/contacto", "/faq",
  "/terminos", "/privacidad", "/cookies",
];

export function CursorController() {
  const pathname = usePathname();
  const showCursor = PUBLIC_PATHS.includes(pathname);

  if (!showCursor) return null;

  return (
    <>
      <CadCursor />
      <style dangerouslySetInnerHTML={{
        __html: `
          body { cursor: none !important; }
          a, button, input, textarea, select { cursor: none !important; }
        `,
      }} />
    </>
  );
}
