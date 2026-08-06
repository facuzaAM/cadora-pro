"use client";

import { useEffect, useRef, useState } from "react";

export function CadCursor() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      setPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    };
    const onLeave = () => setPos(null);
    el.addEventListener("mousemove", onMove);
    el.addEventListener("mouseleave", onLeave);
    return () => {
      el.removeEventListener("mousemove", onMove);
      el.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="pointer-events-none absolute inset-0 z-[1] hidden overflow-hidden lg:block"
      aria-hidden="true"
    >
      {pos && (
        <>
          <div className="absolute inset-x-0 h-px bg-primary/20" style={{ top: pos.y }} />
          <div className="absolute inset-y-0 w-px bg-primary/20" style={{ left: pos.x }} />
        </>
      )}
    </div>
  );
}
