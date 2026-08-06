export function CadCrosshair({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <line x1="50" y1="6" x2="50" y2="94" />
      <line x1="6" y1="50" x2="94" y2="50" />
      <line x1="50" y1="44" x2="50" y2="56" strokeWidth="2.5" />
      <line x1="44" y1="50" x2="56" y2="50" strokeWidth="2.5" />
      <g strokeWidth="1">
        <line x1="50" y1="6" x2="50" y2="12" />
        <line x1="50" y1="88" x2="50" y2="94" />
        <line x1="6" y1="50" x2="12" y2="50" />
        <line x1="88" y1="50" x2="94" y2="50" />
      </g>
      <line x1="50" y1="6" x2="50" y2="12" strokeOpacity="0.5" />
      <line x1="6" y1="50" x2="12" y2="50" strokeOpacity="0.5" />
    </svg>
  );
}
