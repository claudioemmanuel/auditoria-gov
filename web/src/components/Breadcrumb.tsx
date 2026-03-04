import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="flex flex-wrap items-center gap-1.5 text-sm text-muted" aria-label="Breadcrumb">
      <Link href="/" className="inline-flex items-center gap-1 rounded-md px-1 py-0.5 hover:bg-surface-subtle hover:text-secondary">
        <Home className="h-3.5 w-3.5" />
        <span className="sr-only">Inicio</span>
      </Link>
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1">
          <ChevronRight className="h-3.5 w-3.5 text-border" />
          {item.href ? (
            <Link href={item.href} className="rounded-md px-1 py-0.5 hover:bg-surface-subtle hover:text-secondary">
              {item.label}
            </Link>
          ) : (
            <span className="rounded-md px-1.5 py-0.5 font-medium text-primary">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
