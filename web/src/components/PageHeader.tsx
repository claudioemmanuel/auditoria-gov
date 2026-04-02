import { clsx } from "clsx";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  /** @deprecated Use description instead */
  subtitle?: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({ eyebrow, title, subtitle, description, breadcrumbs, actions, className }: PageHeaderProps) {
  const desc = description ?? subtitle;
  return (
    <div className={clsx("flex flex-col gap-1.5", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-1 text-xs text-[var(--color-text-3)]">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <ChevronRight size={12} />}
              {crumb.href ? (
                <Link href={crumb.href} className="hover:text-[var(--color-text-1)] transition-colors">
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-[var(--color-text-2)]">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="ow-page-header flex-between gap-4 flex-wrap">
        <div className="min-w-0">
          {eyebrow && <p className="ow-page-header-eyebrow">{eyebrow}</p>}
          <h1 className="ow-page-header-title">{title}</h1>
          {desc && <p className="ow-page-header-desc">{desc}</p>}
        </div>
        {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
