import { forwardRef } from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

type ButtonVariant = "primary" | "secondary" | "tertiary" | "destructive" | "link" | "ghost";
type ButtonSize = "sm" | "md" | "lg" | "icon";

/**
 * Button Component — Modern Minimalist Design
 * 
 * Variants:
 * - primary: Red alert accent (strong CTA)
 * - secondary: Gray surface (secondary action)
 * - tertiary: Red text only (soft action)
 * - destructive: Red variant for delete/remove
 * - ghost: No background, no border
 * - link: Text link with underline on hover
 */

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--color-accent-alert)] text-white font-medium " +
    "hover:brightness-95 active:brightness-90 " +
    "focus-visible:shadow-[var(--shadow-focus)] " +
    "transition-all duration-150",

  secondary:
    "bg-[var(--color-surface-hover)] text-[var(--color-text-primary)] font-medium " +
    "border border-[var(--color-border-light)] " +
    "hover:bg-[var(--color-surface-active)] " +
    "focus-visible:shadow-[var(--shadow-focus)] " +
    "transition-all duration-150",

  tertiary:
    "text-[var(--color-accent-alert)] font-medium " +
    "hover:bg-[var(--color-accent-dim)] " +
    "focus-visible:shadow-[var(--shadow-focus)] " +
    "transition-all duration-150",

  destructive:
    "bg-[var(--color-destructive)] text-white font-medium " +
    "hover:brightness-95 active:brightness-90 " +
    "focus-visible:shadow-[var(--shadow-focus)] " +
    "transition-all duration-150",

  ghost:
    "text-[var(--color-text-primary)] " +
    "hover:bg-[var(--color-surface-hover)] " +
    "focus-visible:shadow-[var(--shadow-focus)] " +
    "transition-all duration-150",

  link:
    "text-[var(--color-accent-trust)] underline-offset-2 " +
    "hover:underline " +
    "focus-visible:underline " +
    "transition-all duration-150",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm:   "h-8 px-3 text-xs font-medium rounded-[var(--radius-sm)] gap-1.5",
  md:   "h-10 px-4 text-sm font-medium rounded-[var(--radius-sm)] gap-2",
  lg:   "h-12 px-6 text-base font-medium rounded-[var(--radius-sm)] gap-2",
  icon: "h-10 w-10 p-0 items-center justify-center rounded-[var(--radius-sm)]",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    className, 
    variant = "primary", 
    size = "md", 
    loading, 
    disabled, 
    children, 
    ...props 
  }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap font-family-sans",
          "focus-visible:outline-none",
          "disabled:opacity-60 disabled:cursor-not-allowed",
          VARIANT_CLASSES[variant],
          SIZE_CLASSES[size],
          className,
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";

