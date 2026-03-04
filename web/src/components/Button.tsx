import { forwardRef } from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "destructive" | "link";
type ButtonSize = "sm" | "md" | "lg" | "icon";

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-white shadow-sm hover:bg-accent-hover active:bg-accent-hover",
  secondary:
    "border border-border bg-surface-card text-secondary shadow-sm hover:bg-surface-subtle hover:text-primary",
  ghost:
    "text-secondary hover:bg-surface-subtle hover:text-primary",
  destructive:
    "bg-error text-white shadow-sm hover:bg-error/90",
  link:
    "text-accent underline-offset-4 hover:underline",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-8 gap-1.5 rounded-[8px] px-3 text-xs font-medium",
  md: "h-9 gap-2 rounded-[10px] px-4 text-sm font-medium",
  lg: "h-10 gap-2 rounded-[10px] px-6 text-sm font-medium",
  icon: "h-9 w-9 rounded-[10px] items-center justify-center",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap transition-colors duration-120",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1",
          "disabled:pointer-events-none disabled:opacity-50",
          VARIANT_CLASSES[variant],
          SIZE_CLASSES[size],
          className,
        )}
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
