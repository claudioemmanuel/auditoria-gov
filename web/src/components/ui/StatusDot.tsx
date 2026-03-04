import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const statusDotVariants = cva("inline-block rounded-full", {
  variants: {
    size: {
      sm: "h-1.5 w-1.5",
      md: "h-2 w-2",
      lg: "h-2.5 w-2.5",
    },
    status: {
      ok: "bg-green-500",
      warning: "bg-amber-500",
      error: "bg-red-500",
      stale: "bg-yellow-500",
      pending: "bg-gray-400",
      critical: "bg-severity-critical",
      high: "bg-severity-high",
      medium: "bg-severity-medium",
      low: "bg-severity-low",
    },
  },
  defaultVariants: {
    size: "md",
    status: "ok",
  },
});

interface StatusDotProps extends VariantProps<typeof statusDotVariants> {
  className?: string;
  pulse?: boolean;
}

export function StatusDot({ size, status, className, pulse }: StatusDotProps) {
  return (
    <span
      className={cn(
        statusDotVariants({ size, status }),
        pulse && "animate-pulse",
        className,
      )}
    />
  );
}
