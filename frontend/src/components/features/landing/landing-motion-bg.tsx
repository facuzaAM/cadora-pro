/**
 * Ambient CAD/blueprint background motion for the landing hero.
 *
 * Pure CSS animation (no JS): a handful of small coordinate markers drift
 * gently and a soft vertical scan line sweeps, so the backdrop never feels
 * frozen. Positions are deterministic so the server render matches the client
 * (no hydration mismatch). Disabled automatically under `prefers-reduced-motion`.
 */
type Marker = {
  left: string;
  top: string;
  size: number;
  duration: string;
  delay: string;
  opacity: number;
  driftX: string;
};

const MARKERS: Marker[] = [
  { left: "9%", top: "30%", size: 5, duration: "7s", delay: "0.2s", opacity: 0.55, driftX: "8px" },
  { left: "5%", top: "72%", size: 4, duration: "8.5s", delay: "1.1s", opacity: 0.4, driftX: "-6px" },
  { left: "91%", top: "26%", size: 5, duration: "9s", delay: "0.6s", opacity: 0.6, driftX: "-9px" },
  { left: "94%", top: "68%", size: 4, duration: "7.5s", delay: "1.8s", opacity: 0.45, driftX: "7px" },
  { left: "86%", top: "82%", size: 3, duration: "6.5s", delay: "0.9s", opacity: 0.35, driftX: "-5px" },
  { left: "16%", top: "60%", size: 3, duration: "8s", delay: "2.2s", opacity: 0.35, driftX: "6px" },
  { left: "74%", top: "18%", size: 3, duration: "7.2s", delay: "1.5s", opacity: 0.4, driftX: "5px" },
];

export function LandingMotionBG() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden -z-10">
      {MARKERS.map((m, i) => (
        <div
          key={i}
          className="animate-float-drift absolute"
          style={{
            left: m.left,
            top: m.top,
            ["--float-duration" as string]: m.duration,
            ["--float-delay" as string]: m.delay,
            ["--drift-x" as string]: m.driftX,
            ["--marker-opacity" as string]: String(m.opacity),
          }}
        >
          <div
            className="animate-marker-ring relative rounded-full bg-primary/40"
            style={{
              width: m.size * 2,
              height: m.size * 2,
              ["--ring-duration" as string]: "5.5s",
            }}
          />
        </div>
      ))}

      {/* faint dashed dimension leads, like measurements being drawn */}
      <div
        className="animate-float-drift absolute h-px border-t border-dashed border-primary/15"
        style={{
          left: "4%",
          width: "14%",
          top: "66%",
          ["--float-duration" as string]: "11s",
          ["--float-delay" as string]: "0.4s",
          ["--drift-x" as string]: "12px",
          ["--marker-opacity" as string]: "0.5",
        }}
      />
      <div
        className="animate-float-drift absolute h-px border-t border-dashed border-primary/15"
        style={{
          right: "5%",
          width: "13%",
          top: "40%",
          ["--float-duration" as string]: "12s",
          ["--float-delay" as string]: "1.3s",
          ["--drift-x" as string]: "-10px",
          ["--marker-opacity" as string]: "0.5",
        }}
      />

      {/* plotter-style scanner tracing down the hero */}
      <div className="absolute inset-x-[16%] top-0 h-px animate-scan-sweep bg-gradient-to-r from-transparent via-primary/25 to-transparent" />
    </div>
  );
}
