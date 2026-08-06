export function CadDimension({
  label,
  horizontal = true,
  className,
}: {
  label: string;
  horizontal?: boolean;
  className?: string;
}) {
  if (horizontal) {
    return (
      <svg
        viewBox="0 0 120 56"
        className={className}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        aria-hidden="true"
      >
        <line x1="14" y1="10" x2="14" y2="50" />
        <line x1="106" y1="10" x2="106" y2="50" />
        <line x1="14" y1="24" x2="106" y2="24" />
        <path d="M16 24 L23 18.5 L23 29.5 Z" />
        <path d="M104 24 L97 18.5 L97 29.5 Z" />
        <text
          x="60"
          y="44"
          textAnchor="middle"
          fontSize="13"
          stroke="none"
          fill="currentColor"
        >
          {label}
        </text>
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 56 120"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <line x1="10" y1="14" x2="50" y2="14" />
      <line x1="10" y1="106" x2="50" y2="106" />
      <line x1="24" y1="14" x2="24" y2="106" />
      <path d="M24 16 L18.5 23 L29.5 23 Z" />
      <path d="M24 104 L18.5 97 L29.5 97 Z" />
      <text
        x="42"
        y="64"
        textAnchor="middle"
        fontSize="13"
        stroke="none"
        fill="currentColor"
      >
        {label}
      </text>
    </svg>
  );
}
