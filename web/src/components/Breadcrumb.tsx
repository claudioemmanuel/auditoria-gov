import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { clsx } from "clsx";

interface Crumb {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: Crumb[];
  className?: string;
}

export function Breadcrumb({ items, className }: BreadcrumbProps) {
  return (
    <nav className={clsx("ow-breadcrumb", className)} aria-label="Breadcrumb">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && (
            <ChevronRight
              size={13}
              className="ow-breadcrumb-sep flex-shrink-0"
              aria-hidden="true"
            />
          )}
          {item.href ? (
            <Link href={item.href} className="hover:text-[var(--color-text-2)] transition-colors">
              {item.label}
            </Link>
          ) : (
            <span className="ow-breadcrumb-current">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
