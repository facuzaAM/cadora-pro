"use client";

import { useCallback, useEffect, useRef } from "react";

export function CadCursor() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cursorRef = useRef({ x: 0, y: 0 });
  const targetRef = useRef({ x: 0, y: 0 });
  const rafRef = useRef(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Smooth follow
    const cursor = cursorRef.current;
    const target = targetRef.current;
    cursor.x += (target.x - cursor.x) * 0.15;
    cursor.y += (target.y - cursor.y) * 0.15;

    const { x, y } = cursor;
    const s = 16; // half-size

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Outer circle (scope)
    ctx.beginPath();
    ctx.arc(x, y, 14, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(59, 130, 246, 0.3)";
    ctx.lineWidth = 1;
    ctx.stroke();

    // Crosshair lines
    ctx.strokeStyle = "rgba(59, 130, 246, 0.6)";
    ctx.lineWidth = 1.5;

    // Horizontal
    ctx.beginPath();
    ctx.moveTo(x - s, y);
    ctx.lineTo(x - 4, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x + 4, y);
    ctx.lineTo(x + s, y);
    ctx.stroke();

    // Vertical
    ctx.beginPath();
    ctx.moveTo(x, y - s);
    ctx.lineTo(x, y - 4);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y + 4);
    ctx.lineTo(x, y + s);
    ctx.stroke();

    // Center dot
    ctx.beginPath();
    ctx.arc(x, y, 2, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(59, 130, 246, 0.8)";
    ctx.fill();

    // Measurement ticks
    ctx.strokeStyle = "rgba(59, 130, 246, 0.2)";
    ctx.lineWidth = 0.5;
    for (const d of [8, 12]) {
      ctx.beginPath();
      ctx.moveTo(x - d, y - s - 4);
      ctx.lineTo(x - d, y - s + 4);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x + d, y - s - 4);
      ctx.lineTo(x + d, y - s + 4);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x - s - 4, y - d);
      ctx.lineTo(x - s + 4, y - d);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x - s - 4, y + d);
      ctx.lineTo(x - s + 4, y + d);
      ctx.stroke();
    }

    rafRef.current = requestAnimationFrame(draw);
  }, []);

  useEffect(() => {
    // Inicializar posición al centro de la pantalla
    cursorRef.current = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    targetRef.current = { x: window.innerWidth / 2, y: window.innerHeight / 2 };

    const onMove = (e: MouseEvent) => {
      targetRef.current.x = e.clientX;
      targetRef.current.y = e.clientY;
    };
    const resize = () => {
      const canvas = canvasRef.current;
      if (canvas) {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
      }
    };

    resize();
    window.addEventListener("mousemove", onMove);
    window.addEventListener("resize", resize);
    rafRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(rafRef.current);
    };
  }, [draw]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-[9999] hidden lg:block"
      aria-hidden="true"
    />
  );
}
