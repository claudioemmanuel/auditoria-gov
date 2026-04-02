import { forwardRef } from "react";
import { cn } from "@/lib/utils";

/**
 * Card Component — Modern Container with Modern Styling
 * 
 * Provides a consistent, styled container for content sections.
 * Designed for clean, professional layouts with proper spacing and subtle shadows.
 * 
 * Usage:
 * <Card>
 *   <CardHeader>
 *     <CardTitle>Title</CardTitle>
 *     <CardDescription>Description</CardDescription>
 *   </CardHeader>
 *   <CardContent>
 *     Detailed content here
 *   </CardContent>
 *   <CardFooter>
 *     Actions footer
 *   </CardFooter>
 * </Card>
 */

/* ── Root Card ──────────────────────────────────────────── */
export const Card = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { 
  variant?: "default" | "bordered" | "elevated" | "flat";
  clickable?: boolean;
}>(({ className, variant = "default", clickable, ...props }, ref) => {
  const variantClasses: Record<string, string> = {
    default: `bg-[var(--color-surface-card)] 
              border border-[var(--color-border-light)] 
              shadow-[var(--shadow-sm)] 
              hover:shadow-[var(--shadow-md)] 
              transition-shadow duration-200`,
    bordered: `bg-white 
              border-2 border-[var(--color-border-light)]
              hover:border-[var(--color-accent-alert)]
              transition-colors duration-200`,
    elevated: `bg-[var(--color-surface-card)]
              shadow-[var(--shadow-md)]`,
    flat: `bg-[var(--color-surface-hover)]
           border border-[var(--color-border-light)]`,
  };

  return (
    <div
      ref={ref}
      className={cn(
        "rounded-[var(--radius-md)] p-6",
        variantClasses[variant],
        clickable && "cursor-pointer hover:bg-opacity-70",
        className,
      )}
      {...props}
    />
  );
});
Card.displayName = "Card";

/* ── Header ────────────────────────────────────────────── */
export const CardHeader = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col space-y-1.5 mb-4", className)}
      {...props}
    />
  ),
);
CardHeader.displayName = "CardHeader";

/* ── Title ────────────────────────────────────────────── */
export const CardTitle = forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn(
        "text-lg font-semibold leading-none tracking-tight",
        "font-[var(--font-display)] text-[var(--color-text-primary)]",
        className,
      )}
      {...props}
    />
  ),
);
CardTitle.displayName = "CardTitle";

/* ── Description ───────────────────────────────────────── */
export const CardDescription = forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn(
        "text-sm text-[var(--color-text-secondary)]",
        className,
      )}
      {...props}
    />
  ),
);
CardDescription.displayName = "CardDescription";

/* ── Content ───────────────────────────────────────────── */
export const CardContent = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("text-sm text-[var(--color-text-secondary)]", className)}
      {...props}
    />
  ),
);
CardContent.displayName = "CardContent";

/* ── Footer ────────────────────────────────────────────── */
export const CardFooter = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex items-center justify-between pt-4 border-t border-[var(--color-border-light)]",
        "mt-6",
        className,
      )}
      {...props}
    />
  ),
);
CardFooter.displayName = "CardFooter";

/* ── Metric Card — Specialized ────────────────────────── */
export const MetricCard = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & {
  label: string;
  value: string | number;
  subtext?: string;
  accentColor?: string;
}>(({ label, value, subtext, accentColor = "var(--color-accent-alert)", className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-[var(--radius-md)] p-4 bg-white border border-[var(--color-border-light)]",
      "shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)]",
      "transition-shadow duration-200",
      className,
    )}
    {...props}
  >
    <p className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] font-semibold mb-1">
      {label}
    </p>
    <p
      className="text-2xl font-bold font-[var(--font-display)]"
      style={{ color: accentColor }}
    >
      {value}
    </p>
    {subtext && (
      <p className="text-xs text-[var(--color-text-muted)] mt-2">
        {subtext}
      </p>
    )}
  </div>
));
MetricCard.displayName = "MetricCard";

/* ── Signal Card — Specialized ─────────────────────────── */
export const SignalCard = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & {
  title: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  score?: number;
  description?: string;
}>(({ title, severity, score, description, className, ...props }, ref) => {
  const severityConfig = {
    critical: { color: "var(--color-critical)", bgColor: "#FEE2E2" },
    high: { color: "var(--color-high)", bgColor: "#FEF3C7" },
    medium: { color: "var(--color-medium)", bgColor: "#FEF9E7" },
    low: { color: "var(--color-low)", bgColor: "#DBEAFE" },
    info: { color: "var(--color-accent-trust)", bgColor: "#E0F2FE" },
  };

  const config = severityConfig[severity];

  return (
    <div
      ref={ref}
      className={cn(
        "rounded-[var(--radius-md)] p-4",
        "border-l-4 border border-[var(--color-border-light)]",
        "shadow-[var(--shadow-sm)]",
        className,
      )}
      style={{ borderLeftColor: config.color, backgroundColor: config.bgColor }}
      {...props}
    >
      <div className="flex items-start justify-between mb-2">
        <h4
          className="font-semibold text-sm"
          style={{ color: config.color }}
        >
          {title}
        </h4>
        {score && (
          <span
            className="text-xs font-bold px-2 py-1 rounded-[var(--radius-xs)]"
            style={{ color: config.color, backgroundColor: "rgba(255, 255, 255, 0.5)" }}
          >
            {score}%
          </span>
        )}
      </div>
      {description && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          {description}
        </p>
      )}
    </div>
  );
});
SignalCard.displayName = "SignalCard";
