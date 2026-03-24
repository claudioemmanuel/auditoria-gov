import { forwardRef } from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "destructive" | "danger" | "link";
type ButtonSize = "sm" | "md" | "lg" | "icon";

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "border-none hover:brightness-110 active:brightness-90",
  secondary:
    "border border-border bg-transparent text-primary hover:border-fg",
  ghost:
    "bg-transparent text-secondary hover:text-primary",
  destructive:
    "text-critical",
  danger:
    "text-critical",
  link:
    "text-accent underline-offset-4 hover:underline",
};

const VARIANT_STYLES: Record<ButtonVariant, React.CSSProperties> = {
  primary:     { backgroundColor: "var(--color-accent)", color: "var(--color-bg)", borderRadius: 0 },
  secondary:   { borderRadius: 0 },
  ghost:       { border: "1px solid var(--color-border)", borderRadius: 0 },
  destructive: { border: "1px solid var(--color-critical)", borderRadius: 0 },
  danger:      { border: "1px solid var(--color-critical)", borderRadius: 0 },
  link:        { borderRadius: 0 },
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm:   "h-7 gap-1.5 px-3 text-[11px] font-mono tracking-[0.1em] uppercase",
  md:   "h-9 gap-2 px-4 text-xs font-mono tracking-[0.1em] uppercase",
  lg:   "h-10 gap-2 px-6 text-xs font-mono tracking-[0.1em] uppercase",
  icon: "h-9 w-9 items-center justify-center",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, disabled, style, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap transition-colors duration-100",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1",
          "disabled:pointer-events-none disabled:opacity-50",
          VARIANT_CLASSES[variant],
          SIZE_CLASSES[size],
          className,
        )}
        style={{ ...VARIANT_STYLES[variant], ...style }}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";
