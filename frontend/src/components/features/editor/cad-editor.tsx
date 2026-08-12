"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Move, Pencil, DoorClosed, AppWindow, RotateCw, FlipHorizontal2, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type {
  EditorDoor,
  EditorElements,
  EditorText,
  EditorWall,
  EditorWindow,
} from "@/types/editor";

const SNAP_DEG = 8;
const DOOR_COLOR = "#2563eb";
const WINDOW_COLOR = "#059669";
const SELECT_COLOR = "#f59e0b";
const MIN_WIDTH = 10;
const MIN_HEIGHT = 4;

export type EditorTool = "select" | "wall" | "door" | "window";

interface CadEditorProps {
  imageUrl: string;
  width: number;
  height: number;
  initial: EditorElements;
  measurements?: EditorText[];
  onSave: (elements: EditorElements) => Promise<void>;
  onExport: (elements: EditorElements) => Promise<void>;
  saving?: boolean;
  exporting?: boolean;
}

interface Selected {
  kind: "wall" | "door" | "window";
  id: string;
}

interface DoorGeo {
  hx: number;
  hy: number;
  gx2: number;
  gy2: number;
  lx: number;
  ly: number;
}

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `id-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

function doorGeometry(d: EditorDoor): DoorGeo {
  const rad = (d.rotation * Math.PI) / 180;
  const gx = Math.cos(rad);
  const gy = Math.sin(rad);
  const px = -gy;
  const py = gx;
  const w = d.width;
  const s = d.swing === "right" ? 1 : -1;
  return {
    hx: d.x - (w / 2) * gx,
    hy: d.y - (w / 2) * gy,
    gx2: d.x + (w / 2) * gx,
    gy2: d.y + (w / 2) * gy,
    lx: d.x - (w / 2) * gx + w * px * s,
    ly: d.y - (w / 2) * gy + w * py * s,
  };
}

function windowAxis(d: EditorWindow) {
  const rad = (d.rotation * Math.PI) / 180;
  return {
    gx: Math.cos(rad),
    gy: Math.sin(rad),
    px: -Math.sin(rad),
    py: Math.cos(rad),
  };
}

function snapWallEnd(x1: number, y1: number, x2: number, y2: number) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const ang = (Math.atan2(dy, dx) * 180) / Math.PI;
  const snapped = Math.round(ang / 45) * 45;
  if (Math.abs(ang - snapped) <= SNAP_DEG) {
    const len = Math.hypot(dx, dy);
    const rad = (snapped * Math.PI) / 180;
    return { x: x1 + len * Math.cos(rad), y: y1 + len * Math.sin(rad) };
  }
  return { x: x2, y: y2 };
}

function snapAxisAngle(ang: number): number {
  const snapped = Math.round(ang / 90) * 90;
  return Math.abs(ang - snapped) <= SNAP_DEG ? snapped : ang;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function CadEditor({
  imageUrl,
  width,
  height,
  initial,
  measurements = [],
  onSave,
  onExport,
  saving = false,
  exporting = false,
}: CadEditorProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const [walls, setWalls] = useState<EditorWall[]>(initial.walls);
  const [doors, setDoors] = useState<EditorDoor[]>(initial.doors);
  const [windows, setWindows] = useState<EditorWindow[]>(initial.windows);
  const [tool, setTool] = useState<EditorTool>("select");
  const [selected, setSelected] = useState<Selected | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [coarse, setCoarse] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(pointer: coarse)");
    const update = () => setCoarse(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const touchScale = coarse ? 1.7 : 1;

  const draftRef = useRef<{
    kind: "draw-wall" | "draw-door" | "draw-window" | "move" | "resize";
    startX: number;
    startY: number;
    id: string | null;
    initial?: unknown;
  } | null>(null);

  const elements = useMemo<EditorElements>(
    () => ({ walls, doors, windows }),
    [walls, doors, windows],
  );

  const strokeW = clamp(width / 500, 2, 6);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Delete" || e.key === "Backspace") {
        if (selected) {
          e.preventDefault();
          deleteSelected();
        }
      }
      if (e.key === "Escape") {
        setSelected(null);
        setTool("select");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const toUser = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const user = pt.matrixTransform(ctm.inverse());
    return { x: user.x, y: user.y };
  }, []);

  const hitTest = useCallback(
    (x: number, y: number): Selected | null => {
      const radius = Math.max(8, strokeW * 2.5) * touchScale;
      for (const w of windows) {
        const { gx, gy, px, py } = windowAxis(w);
        const dx = x - w.x;
        const dy = y - w.y;
        const along = Math.abs(dx * gx + dy * gy);
        const across = Math.abs(dx * px + dy * py);
        if (along <= w.width / 2 + radius && across <= w.height / 2 + radius) {
          return { kind: "window", id: w.id };
        }
      }
      for (const d of doors) {
        if (Math.hypot(x - d.x, y - d.y) <= Math.max(d.width, 20) / 2 + radius) {
          return { kind: "door", id: d.id };
        }
      }
      for (const wall of walls) {
        const dx = wall.x2 - wall.x1;
        const dy = wall.y2 - wall.y1;
        const len = Math.hypot(dx, dy);
        if (len === 0) continue;
        const t = clamp(((x - wall.x1) * dx + (y - wall.y1) * dy) / (len * len), 0, 1);
        const px = wall.x1 + t * dx;
        const py = wall.y1 + t * dy;
        const dist = Math.hypot(x - px, y - py);
        if (dist <= radius) {
          return { kind: "wall", id: wall.id };
        }
      }
      return null;
    },
    [walls, doors, windows, strokeW, touchScale],
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      const pos = toUser(e.clientX, e.clientY);
      e.currentTarget.setPointerCapture(e.pointerId);

      if (tool === "select") {
        const hit = hitTest(pos.x, pos.y);
        if (hit) {
          setSelected(hit);
          const initial =
            hit.kind === "wall"
              ? {
                  kind: "wall" as const,
                  id: hit.id,
                  x1: walls.find((w) => w.id === hit.id)?.x1,
                  y1: walls.find((w) => w.id === hit.id)?.y1,
                  x2: walls.find((w) => w.id === hit.id)?.x2,
                  y2: walls.find((w) => w.id === hit.id)?.y2,
                }
              : hit.kind === "door"
                ? {
                    kind: "door" as const,
                    id: hit.id,
                    x: doors.find((d) => d.id === hit.id)?.x,
                    y: doors.find((d) => d.id === hit.id)?.y,
                  }
                : {
                    kind: "window" as const,
                    id: hit.id,
                    x: windows.find((w) => w.id === hit.id)?.x,
                    y: windows.find((w) => w.id === hit.id)?.y,
                  };
          draftRef.current = {
            kind: "move",
            startX: pos.x,
            startY: pos.y,
            id: hit.id,
            initial,
          };
          e.preventDefault();
        } else {
          setSelected(null);
        }
        return;
      }

      if (tool === "wall") {
        draftRef.current = { kind: "draw-wall", startX: pos.x, startY: pos.y, id: null };
        setSelected(null);
        return;
      }
      if (tool === "door") {
        draftRef.current = { kind: "draw-door", startX: pos.x, startY: pos.y, id: null };
        setSelected(null);
        return;
      }
      if (tool === "window") {
        draftRef.current = { kind: "draw-window", startX: pos.x, startY: pos.y, id: null };
        setSelected(null);
      }
    },
    [tool, toUser, hitTest, walls, doors, windows],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      const draft = draftRef.current;
      if (!draft) return;
      const pos = toUser(e.clientX, e.clientY);

      if (draft.kind === "draw-wall") {
        const end = snapWallEnd(draft.startX, draft.startY, pos.x, pos.y);
        setWalls((prev) => {
          const next = prev.filter((w) => w.id !== "__draft__");
          return [
            ...next,
            {
              id: "__draft__",
              x1: draft.startX,
              y1: draft.startY,
              x2: end.x,
              y2: end.y,
            },
          ];
        });
        return;
      }

      if (draft.kind === "draw-door") {
        const dx = pos.x - draft.startX;
        const dy = pos.y - draft.startY;
        const ang = (Math.atan2(dy, dx) * 180) / Math.PI;
        const rotation = snapAxisAngle(ang);
        const len = Math.max(MIN_WIDTH, Math.hypot(dx, dy));
        setDoors((prev) => {
          const next = prev.filter((d) => d.id !== "__draft__");
          return [
            ...next,
            {
              id: "__draft__",
              type: "single",
              x: draft.startX,
              y: draft.startY,
              width: len,
              rotation,
              swing: "right",
            },
          ];
        });
        return;
      }

      if (draft.kind === "draw-window") {
        const dx = pos.x - draft.startX;
        const dy = pos.y - draft.startY;
        const ang = (Math.atan2(dy, dx) * 180) / Math.PI;
        const rotation = snapAxisAngle(ang);
        const len = Math.max(MIN_WIDTH, Math.hypot(dx, dy));
        setWindows((prev) => {
          const next = prev.filter((w) => w.id !== "__draft__");
          return [
            ...next,
            {
              id: "__draft__",
              type: "sliding",
              x: draft.startX,
              y: draft.startY,
              width: len,
              height: Math.max(MIN_HEIGHT, len / 8),
              rotation,
            },
          ];
        });
        return;
      }

      if (draft.kind === "move" && draft.initial) {
        const dx = pos.x - draft.startX;
        const dy = pos.y - draft.startY;
        const ini = draft.initial as {
          kind: "wall" | "door" | "window";
          id: string;
          x1?: number;
          y1?: number;
          x2?: number;
          y2?: number;
          x?: number;
          y?: number;
        };
        if (ini.kind === "wall" && ini.x1 !== undefined && ini.y1 !== undefined && ini.x2 !== undefined && ini.y2 !== undefined) {
          setWalls((prev) =>
            prev.map((w) =>
              w.id === selected?.id
                ? { ...w, x1: ini.x1! + dx, y1: ini.y1! + dy, x2: ini.x2! + dx, y2: ini.y2! + dy }
                : w,
            ),
          );
        } else if (ini.kind === "door" && ini.x !== undefined && ini.y !== undefined) {
          setDoors((prev) =>
            prev.map((d) =>
              d.id === selected?.id ? { ...d, x: ini.x! + dx, y: ini.y! + dy } : d,
            ),
          );
        } else if (ini.kind === "window" && ini.x !== undefined && ini.y !== undefined) {
          setWindows((prev) =>
            prev.map((w) =>
              w.id === selected?.id ? { ...w, x: ini.x! + dx, y: ini.y! + dy } : w,
            ),
          );
        }
        return;
      }

      if (draft.kind === "resize" && draft.initial) {
        const ini = draft.initial as {
          kind: "door" | "window" | "wall";
          mode: string;
          id: string;
        };
        const dx = pos.x - draft.startX;
        const dy = pos.y - draft.startY;

        if (ini.kind === "wall" && ini.mode === "endpoint") {
          const wall = walls.find((w) => w.id === ini.id);
          if (!wall) return;
          const moved = { x: draft.startX + dx, y: draft.startY + dy };
          if (draft.id === "end2") {
            const snapPoint = snapWallEnd(wall.x1, wall.y1, moved.x, moved.y);
            setWalls((prev) =>
              prev.map((w) =>
                w.id === ini.id ? { ...w, x2: snapPoint.x, y2: snapPoint.y } : w,
              ),
            );
          } else {
            const snapPoint = snapWallEnd(wall.x2, wall.y2, moved.x, moved.y);
            setWalls((prev) =>
              prev.map((w) =>
                w.id === ini.id ? { ...w, x1: snapPoint.x, y1: snapPoint.y } : w,
              ),
            );
          }
          return;
        }

        if (ini.kind === "door" && ini.mode === "width") {
          const door = doors.find((d) => d.id === ini.id);
          if (!door) return;
          const rad = (door.rotation * Math.PI) / 180;
          const gx = Math.cos(rad);
          const gy = Math.sin(rad);
          const along = (pos.x - door.x) * gx + (pos.y - door.y) * gy;
          setDoors((prev) =>
            prev.map((d) =>
              d.id === ini.id ? { ...d, width: clamp(2 * Math.abs(along), MIN_WIDTH, 100000) } : d,
            ),
          );
          return;
        }

        if (ini.kind === "window" && ini.mode === "width") {
          const win = windows.find((w) => w.id === ini.id);
          if (!win) return;
          const { gx, gy } = windowAxis(win);
          const along = (pos.x - win.x) * gx + (pos.y - win.y) * gy;
          setWindows((prev) =>
            prev.map((w) =>
              w.id === ini.id ? { ...w, width: clamp(2 * Math.abs(along), MIN_WIDTH, 100000) } : w,
            ),
          );
          return;
        }

        if (ini.kind === "window" && ini.mode === "height") {
          const win = windows.find((w) => w.id === ini.id);
          if (!win) return;
          const { px, py } = windowAxis(win);
          const across = (pos.x - win.x) * px + (pos.y - win.y) * py;
          setWindows((prev) =>
            prev.map((w) =>
              w.id === ini.id ? { ...w, height: clamp(2 * Math.abs(across), MIN_HEIGHT, 100000) } : w,
            ),
          );
        }
      }
    },
    [toUser, selected, walls, doors, windows],
  );

  const handlePointerUp = useCallback(() => {
    const draft = draftRef.current;
    if (!draft) return;
    if (draft.kind === "draw-wall") {
      setWalls((prev) => {
        const draftWall = prev.find((w) => w.id === "__draft__");
        const rest = prev.filter((w) => w.id !== "__draft__");
        if (!draftWall) return prev;
        const len = Math.hypot(draftWall.x2 - draftWall.x1, draftWall.y2 - draftWall.y1);
        if (len < 4) return prev;
        const newWall = { ...draftWall, id: uuid() };
        setSelected({ kind: "wall", id: newWall.id });
        setDirty(true);
        return [...rest, newWall];
      });
    }
    if (draft.kind === "draw-door") {
      setDoors((prev) => {
        const draftDoor = prev.find((d) => d.id === "__draft__");
        const rest = prev.filter((d) => d.id !== "__draft__");
        if (!draftDoor || draftDoor.width < MIN_WIDTH) return prev;
        const newDoor = { ...draftDoor, id: uuid() };
        setSelected({ kind: "door", id: newDoor.id });
        setDirty(true);
        return [...rest, newDoor];
      });
    }
    if (draft.kind === "draw-window") {
      setWindows((prev) => {
        const draftWin = prev.find((w) => w.id === "__draft__");
        const rest = prev.filter((w) => w.id !== "__draft__");
        if (!draftWin || draftWin.width < MIN_WIDTH) return prev;
        const newWin = { ...draftWin, id: uuid() };
        setSelected({ kind: "window", id: newWin.id });
        setDirty(true);
        return [...rest, newWin];
      });
    }
    if (draft.kind === "move" || draft.kind === "resize") {
      setDirty(true);
    }
    draftRef.current = null;
  }, []);

  const deleteSelected = useCallback(() => {
    if (!selected) return;
    if (selected.kind === "wall") {
      setWalls((prev) => prev.filter((w) => w.id !== selected.id));
    } else if (selected.kind === "door") {
      setDoors((prev) => prev.filter((d) => d.id !== selected.id));
    } else {
      setWindows((prev) => prev.filter((w) => w.id !== selected.id));
    }
    setSelected(null);
    setDirty(true);
  }, [selected]);

  const rotateSelected = useCallback(() => {
    if (!selected) return;
    const step = selected.kind === "wall" ? 45 : 90;
    if (selected.kind === "door") {
      setDoors((prev) =>
        prev.map((d) => (d.id === selected.id ? { ...d, rotation: d.rotation + step } : d)),
      );
    } else if (selected.kind === "window") {
      setWindows((prev) =>
        prev.map((w) => (w.id === selected.id ? { ...w, rotation: w.rotation + step } : w)),
      );
    }
    setDirty(true);
  }, [selected]);

  const flipSwing = useCallback(() => {
    if (!selected || selected.kind !== "door") return;
    setDoors((prev) =>
      prev.map((d) =>
        d.id === selected.id ? { ...d, swing: d.swing === "right" ? "left" : "right" } : d,
      ),
    );
    setDirty(true);
  }, [selected]);

  const selectedDoor = useMemo(
    () => doors.find((d) => d.id === selected?.id),
    [doors, selected],
  );
  const selectedWindow = useMemo(
    () => windows.find((w) => w.id === selected?.id),
    [windows, selected],
  );
  const selectedWall = useMemo(
    () => walls.find((w) => w.id === selected?.id),
    [walls, selected],
  );

  const onResizeStart = useCallback(
    (e: React.PointerEvent, kind: "door" | "window" | "wall", mode: string, id: string, endpoint?: string) => {
      e.stopPropagation();
      const pos = toUser(e.clientX, e.clientY);
      draftRef.current = {
        kind: "resize",
        startX: pos.x,
        startY: pos.y,
        id: endpoint ?? id,
        initial: { kind, mode, id },
      };
    },
    [toUser],
  );

  const tools: { id: EditorTool; label: string; icon: React.ReactNode }[] = [
    { id: "select", label: "Seleccionar", icon: <Move className="h-4 w-4" /> },
    { id: "wall", label: "Muro", icon: <Pencil className="h-4 w-4" /> },
    { id: "door", label: "Puerta", icon: <DoorClosed className="h-4 w-4" /> },
    { id: "window", label: "Ventana", icon: <AppWindow className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-card p-2">
        {tools.map((t) => (
          <button
            key={t.id}
            type="button"
            aria-pressed={tool === t.id}
            aria-label={t.label}
            title={t.label}
            onClick={() => {
              setTool(t.id);
              setSelected(null);
              draftRef.current = null;
            }}
            className={cn(
              "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              tool === t.id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Badge variant="secondary">{walls.length} muros</Badge>
          <Badge variant="secondary">{doors.length} puertas</Badge>
          <Badge variant="secondary">{windows.length} ventanas</Badge>
          {dirty && <Badge variant="outline" className="text-amber-500">sin guardar</Badge>}
        </div>
      </div>

      <div className="relative overflow-hidden rounded-xl border bg-grid-cad">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width || 1} ${height || 1}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Editor de plano: arrastrá para dibujar muros, puertas y ventanas. Usá la herramienta seleccionar para mover o redimensionar elementos."
          className="block w-full touch-none select-none"
          style={{ maxHeight: "75vh", cursor: tool === "select" ? "default" : "crosshair" }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          {imageUrl && (
            <image href={imageUrl} x={0} y={0} width={width} height={height} preserveAspectRatio="xMidYMid meet" opacity={0.55} />
          )}

          <g pointerEvents="none" fill="none" stroke="#6b7280" strokeWidth={Math.max(1, strokeW / 2)} opacity={0.5}>
            {measurements.map((m, i) => {
              const [x1, y1, x2, y2] = m.bbox;
              const cx = (x1 + x2) / 2;
              const cy = (y1 + y2) / 2;
              return (
                <text
                  key={`m-${i}`}
                  x={cx}
                  y={cy}
                  fontSize={Math.max(8, strokeW * 1.6)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#6b7280"
                  stroke="none"
                >
                  {m.text}
                </text>
              );
            })}
          </g>

          <g strokeLinecap="round" pointerEvents={tool === "select" ? "auto" : "none"}>
            {walls.map((wall) => {
              const isSelected = selected?.kind === "wall" && selected.id === wall.id;
              const isHover = hoverId === wall.id;
              return (
                <line
                  key={wall.id}
                  x1={wall.x1}
                  y1={wall.y1}
                  x2={wall.x2}
                  y2={wall.y2}
                  stroke={isSelected || isHover ? SELECT_COLOR : "#1e293b"}
                  strokeWidth={isSelected ? strokeW * 1.4 : strokeW}
                  opacity={0.9}
                  onPointerDown={(e) => {
                    if (tool === "select") {
                      e.stopPropagation();
                      setSelected({ kind: "wall", id: wall.id });
                      const pos = toUser(e.clientX, e.clientY);
                      draftRef.current = { kind: "move", startX: pos.x, startY: pos.y, id: wall.id };
                      e.preventDefault();
                    }
                  }}
                  onPointerEnter={() => setHoverId(wall.id)}
                  onPointerLeave={() => setHoverId(null)}
                />
              );
            })}
          </g>

          <g pointerEvents={tool === "select" ? "auto" : "none"}>
            {doors.map((door) => {
              const isSelected = selected?.kind === "door" && selected.id === door.id;
              const isHover = hoverId === door.id;
              const geo = doorGeometry(door);
              const color = isSelected || isHover ? SELECT_COLOR : DOOR_COLOR;
              const lw = strokeW * 0.9;
              return (
                <g
                  key={door.id}
                  onPointerDown={(e) => {
                    if (tool === "select") {
                      e.stopPropagation();
                      setSelected({ kind: "door", id: door.id });
                      const pos = toUser(e.clientX, e.clientY);
                      draftRef.current = { kind: "move", startX: pos.x, startY: pos.y, id: door.id };
                      e.preventDefault();
                    }
                  }}
                  onPointerEnter={() => setHoverId(door.id)}
                  onPointerLeave={() => setHoverId(null)}
                >
                  <line x1={geo.hx} y1={geo.hy} x2={geo.gx2} y2={geo.gy2} stroke={color} strokeWidth={lw} />
                  {door.type !== "sliding" && (
                    <>
                      <line x1={geo.hx} y1={geo.hy} x2={geo.lx} y2={geo.ly} stroke={color} strokeWidth={lw} />
                      <path
                        d={`M ${geo.gx2} ${geo.gy2} A ${door.width} ${door.width} 0 0 ${door.swing === "right" ? 1 : 0} ${geo.lx} ${geo.ly}`}
                        fill="none"
                        stroke={color}
                        strokeWidth={lw * 0.7}
                        strokeDasharray={isSelected ? undefined : "6 4"}
                      />
                    </>
                  )}
                  <rect
                    x={door.x - strokeW * 2}
                    y={door.y - strokeW * 2}
                    width={strokeW * 4}
                    height={strokeW * 4}
                    rx={1}
                    fill={color}
                  />
                </g>
              );
            })}
          </g>

          <g pointerEvents={tool === "select" ? "auto" : "none"}>
            {windows.map((win) => {
              const isSelected = selected?.kind === "window" && selected.id === win.id;
              const isHover = hoverId === win.id;
              const color = isSelected || isHover ? SELECT_COLOR : WINDOW_COLOR;
              const { gx, gy } = windowAxis(win);
              const lw = strokeW * 0.9;
              const cx = win.x;
              const cy = win.y;
              return (
                <g
                  key={win.id}
                  onPointerDown={(e) => {
                    if (tool === "select") {
                      e.stopPropagation();
                      setSelected({ kind: "window", id: win.id });
                      const pos = toUser(e.clientX, e.clientY);
                      draftRef.current = { kind: "move", startX: pos.x, startY: pos.y, id: win.id };
                      e.preventDefault();
                    }
                  }}
                  onPointerEnter={() => setHoverId(win.id)}
                  onPointerLeave={() => setHoverId(null)}
                >
                  <rect
                    x={cx - win.width / 2}
                    y={cy - win.height / 2}
                    width={win.width}
                    height={win.height}
                    fill="none"
                    stroke={color}
                    strokeWidth={lw}
                    transform={`rotate(${win.rotation} ${cx} ${cy})`}
                  />
                  {win.type === "sliding" && (
                    <line
                      x1={cx - (win.width / 2) * gx}
                      y1={cy - (win.width / 2) * gy}
                      x2={cx + (win.width / 2) * gx}
                      y2={cy + (win.width / 2) * gy}
                      stroke={color}
                      strokeWidth={lw * 0.5}
                    />
                  )}
                  <circle cx={cx} cy={cy} r={Math.max(2, strokeW * 0.6)} fill={color} />
                </g>
              );
            })}
          </g>

          {(selected?.kind === "wall" && selectedWall) && (
            <g pointerEvents="none">
              {[
                { hx: selectedWall.x1, hy: selectedWall.y1, mode: "end1" },
                { hx: selectedWall.x2, hy: selectedWall.y2, mode: "end2" },
              ].map((h) => (
                <circle
                  key={h.mode}
                  cx={h.hx}
                  cy={h.hy}
                  r={Math.max(5, strokeW * 1.4) * touchScale}
                  fill="#fff"
                  stroke={SELECT_COLOR}
                  strokeWidth={2}
                  className="pointer-events-auto cursor-nwse-resize"
                  onPointerDown={(e) => onResizeStart(e, "wall", "endpoint", selectedWall.id, h.mode)}
                />
              ))}
            </g>
          )}

          {(selected?.kind === "door" && selectedDoor) && (
            <g>
              {(() => {
                const geo = doorGeometry(selectedDoor);
                return (
                  <circle
                    cx={geo.gx2}
                    cy={geo.gy2}
                    r={Math.max(5, strokeW * 1.4) * touchScale}
                    fill="#fff"
                    stroke={SELECT_COLOR}
                    strokeWidth={2}
                    className="cursor-ew-resize"
                    onPointerDown={(e) => onResizeStart(e, "door", "width", selectedDoor.id)}
                  />
                );
              })()}
            </g>
          )}

          {(selected?.kind === "window" && selectedWindow) && (
            <g>
              {(() => {
                const { gx, gy, px, py } = windowAxis(selectedWindow);
                return (
                  <>
                    <circle
                      cx={selectedWindow.x + (selectedWindow.width / 2) * gx}
                      cy={selectedWindow.y + (selectedWindow.width / 2) * gy}
                      r={Math.max(5, strokeW * 1.4) * touchScale}
                      fill="#fff"
                      stroke={SELECT_COLOR}
                      strokeWidth={2}
                      className="cursor-ew-resize"
                      onPointerDown={(e) => onResizeStart(e, "window", "width", selectedWindow.id)}
                    />
                    <circle
                      cx={selectedWindow.x + (selectedWindow.height / 2) * px}
                      cy={selectedWindow.y + (selectedWindow.height / 2) * py}
                      r={Math.max(5, strokeW * 1.4) * touchScale}
                      fill="#fff"
                      stroke={SELECT_COLOR}
                      strokeWidth={2}
                      className="cursor-ns-resize"
                      onPointerDown={(e) => onResizeStart(e, "window", "height", selectedWindow.id)}
                    />
                  </>
                );
              })()}
            </g>
          )}
        </svg>
      </div>

      {selected && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-card p-2">
          <span className="px-2 text-sm font-medium capitalize text-muted-foreground">
            {selected.kind}
          </span>
          {selected.kind === "wall" && (
            <Button variant="outline" size="sm" onClick={rotateSelected}>
              <RotateCw className="mr-2 h-4 w-4" />
              Rotar 45°
            </Button>
          )}
          {selected.kind === "door" && (
            <>
              <Button variant="outline" size="sm" onClick={rotateSelected}>
                <RotateCw className="mr-2 h-4 w-4" />
                Rotar 90°
              </Button>
              <Button variant="outline" size="sm" onClick={flipSwing}>
                <FlipHorizontal2 className="mr-2 h-4 w-4" />
                Invertir giro
              </Button>
              <select
                value={selectedDoor?.type ?? "single"}
                onChange={(e) => {
                  if (!selectedDoor) return;
                  setDoors((prev) =>
                    prev.map((d) =>
                      d.id === selectedDoor.id
                        ? { ...d, type: e.target.value as EditorDoor["type"] }
                        : d,
                    ),
                  );
                  setDirty(true);
                }}
                className="h-9 rounded-lg border bg-background px-2 text-sm"
              >
                <option value="single">Puerta simple</option>
                <option value="double">Puerta doble</option>
                <option value="sliding">Corrediza</option>
              </select>
              <span className="text-xs text-muted-foreground">
                Ancho: {Math.round(selectedDoor?.width ?? 0)} px
              </span>
            </>
          )}
          {selected.kind === "window" && (
            <>
              <Button variant="outline" size="sm" onClick={rotateSelected}>
                <RotateCw className="mr-2 h-4 w-4" />
                Rotar 90°
              </Button>
              <select
                value={selectedWindow?.type ?? "sliding"}
                onChange={(e) => {
                  if (!selectedWindow) return;
                  setWindows((prev) =>
                    prev.map((w) =>
                      w.id === selectedWindow.id
                        ? { ...w, type: e.target.value as EditorWindow["type"] }
                        : w,
                    ),
                  );
                  setDirty(true);
                }}
                className="h-9 rounded-lg border bg-background px-2 text-sm"
              >
                <option value="sliding">Corredera</option>
                <option value="fixed">Fija</option>
                <option value="casement">Batiente</option>
              </select>
              <span className="text-xs text-muted-foreground">
                {Math.round(selectedWindow?.width ?? 0)} × {Math.round(selectedWindow?.height ?? 0)} px
              </span>
            </>
          )}
          {(selected?.kind === "door" || selected?.kind === "window") && (
            <span className="text-xs text-muted-foreground">
              Confianza:{" "}
              <span
                className={cn(
                  "font-medium",
                  (selected.kind === "door" ? selectedDoor?.confidence : selectedWindow?.confidence) ?? 0 >= 0.65
                    ? "text-emerald-600"
                    : "text-amber-500",
                )}
              >
                {Math.round(((selected.kind === "door" ? selectedDoor?.confidence : selectedWindow?.confidence) ?? 0) * 100)}%
              </span>
            </span>
          )}
          <Button variant="destructive" size="sm" onClick={deleteSelected}>
            <Trash2 className="mr-2 h-4 w-4" />
            Eliminar
          </Button>
          <div className="ml-auto flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={saving}
              onClick={() => onSave(elements).then(() => setDirty(false))}
            >
              {saving ? "Guardando..." : "Guardar cambios"}
            </Button>
            <Button
              size="sm"
              disabled={exporting}
              onClick={() => onExport(elements)}
            >
              {exporting ? "Generando..." : "Exportar DXF"}
            </Button>
          </div>
        </div>
      )}

      {!selected && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border bg-card p-2">
          <p className="px-2 text-xs text-muted-foreground">
            {tool === "select"
              ? "Hacé clic en un elemento para seleccionarlo, arrastralo para moverlo."
              : `Hacé clic y arrastrá para dibujar un ${tool === "wall" ? "muro" : tool}.`}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={saving}
              onClick={() => onSave(elements).then(() => setDirty(false))}
            >
              {saving ? "Guardando..." : "Guardar cambios"}
            </Button>
            <Button size="sm" disabled={exporting} onClick={() => onExport(elements)}>
              {exporting ? "Generando..." : "Exportar DXF"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
