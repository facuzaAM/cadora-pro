import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  showText?: boolean;
}

export function Logo({ className, showText = true }: LogoProps) {
  if (!showText) {
    return (
      <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg bg-primary", className)}>
        <span className="text-sm font-bold text-primary-foreground">C</span>
      </div>
    );
  }

  return (
    <div className={cn("flex items-baseline gap-0", className)}>
      <span className="text-lg font-bold tracking-tight text-foreground">Cadora</span>
      <span className="text-lg font-bold tracking-tight text-primary">.pro</span>
    </div>
  );
}
