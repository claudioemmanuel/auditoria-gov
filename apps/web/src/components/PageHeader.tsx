import { clsx } from "clsx";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderStat {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "default" | "brand" | "success" | "warning" | "danger";
  mono?: boolean;
}

interface PageHeaderProps {
  eyebrow?: string;
  title?: string;
  /** @deprecated Use description instead */
  subtitle?: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: ReactNode;
  className?: string;
  icon?: ReactNode;
  variant?: "default" | "hero";
  stats?: PageHeaderStat[];
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  description,
  breadcrumbs,
  actions,
  className,
  icon,
  variant = "default",
  stats,
}: PageHeaderProps) {
  const desc = description ?? subtitle;
  const hasHeaderContent = Boolean(eyebrow || title || desc || actions || icon || (stats && stats.length > 0));

  return (
    <div className={clsx("flex flex-col gap-1.5", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-1 text-xs text-[var(--color-text-3)]">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <ChevronRight size={12} />}
              {crumb.href ? (
                <Link href={crumb.href} className="hover:text-[var(--color-text)] transition-colors">
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-[var(--color-text-2)]">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}

      {hasHeaderContent && (
        <div className={clsx("ow-page-header", variant === "hero" && "ow-page-header-hero")}>
          <div className="flex-between gap-4 flex-wrap">
            <div className="flex min-w-0 items-start gap-3.5">
              {icon && <div className={clsx("ow-page-header-icon", variant === "hero" && "ow-page-header-icon-hero")}>{icon}</div>}
              <div className="min-w-0">
                {eyebrow && <p className="ow-page-header-eyebrow">{eyebrow}</p>}
                {title && <h1 className="ow-page-header-title">{title}</h1>}
                {desc && <p className="ow-page-header-desc">{desc}</p>}
              </div>
            </div>
            {actions && <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">{actions}</div>}
          </div>

          {stats && stats.length > 0 && (
            <div className="ow-page-header-stats">
              {stats.map((stat, index) => (
                <div key={`${stat.label}-${index}`} className="ow-page-header-stat" data-tone={stat.tone ?? "default"}>
                  <span className="ow-page-header-stat-label">{stat.label}</span>
                  <span className={clsx("ow-page-header-stat-value", stat.mono && "text-mono")}>{stat.value}</span>
                  {stat.sub && <span className="ow-page-header-stat-sub">{stat.sub}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
