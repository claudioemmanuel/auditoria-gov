import { clsx } from "clsx";
import type { HTMLAttributes, ReactNode } from "react";

/* ── Base Card ──────────────────────────────────────────────────── */
interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
  amber?: boolean;
}

export function Card({ hoverable, amber, className, children, ...props }: CardProps) {
  return (
    <div
      className={clsx(
        "ow-card",
        hoverable && "ow-card-hover",
        amber && "ow-card-amber",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/* ── Card Section ───────────────────────────────────────────────── */
interface CardSectionProps extends HTMLAttributes<HTMLDivElement> {}

export function CardSection({ className, children, ...props }: CardSectionProps) {
  return (
    <div className={clsx("ow-card-section", className)} {...props}>
      {children}
    </div>
  );
}

/* ── Card Header / Title / Description (aliases for compatibility) ── */
export function CardHeader({ className, children, ...props }: CardSectionProps) {
  return (
    <div className={clsx("ow-card-section", className)} {...props}>
      {children}
    </div>
  );
}

export function CardContent({ className, children, ...props }: CardSectionProps) {
  return (
    <div className={clsx("ow-card-section pt-0", className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...props }: CardSectionProps) {
  return (
    <div
      className={clsx("ow-card-section border-t border-[var(--color-border)]", className)}
      {...props}
    >
      {children}
    </div>
  );
}

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  as?: "h1" | "h2" | "h3" | "h4";
}

export function CardTitle({ as: Tag = "h3", className, children, ...props }: CardTitleProps) {
  return (
    <Tag
      className={clsx(
        "text-sm font-semibold text-[var(--color-text)] leading-tight",
        className
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}

export function CardDescription({ className, children, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={clsx("text-sm text-[var(--color-text-2)] leading-relaxed", className)}
      {...props}
    >
      {children}
    </p>
  );
}

/* ── Metric Card ────────────────────────────────────────────────── */
interface MetricCardProps {
  label: string;
  value: number | string;
  accentColor?: string;
  sub?: string;
  icon?: ReactNode;
  className?: string;
}

export function MetricCard({ label, value, accentColor, sub, icon, className }: MetricCardProps) {
  return (
    <div
      className={clsx("ow-card ow-card-section flex flex-col gap-1", className)}
      style={accentColor ? { borderTop: `2px solid ${accentColor}` } : undefined}
    >
      {icon && (
        <div className="mb-1 opacity-60" style={{ color: accentColor }}>
          {icon}
        </div>
      )}
      <div
        className="text-display-lg tabular-nums"
        style={{ color: accentColor || "var(--color-text)" }}
      >
        {value}
      </div>
      <div className="text-label text-[var(--color-text-3)]">{label}</div>
      {sub && <div className="text-caption text-[var(--color-text-3)] mt-0.5">{sub}</div>}
    </div>
  );
}
