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
    <nav className="flex items-center gap-1 text-sm text-gov-gray-500" aria-label="Breadcrumb">
      <Link href="/" className="flex items-center gap-1 hover:text-gov-blue-600">
        <Home className="h-3.5 w-3.5" />
        <span className="sr-only">Inicio</span>
      </Link>
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1">
          <ChevronRight className="h-3.5 w-3.5 text-gov-gray-300" />
          {item.href ? (
            <Link href={item.href} className="hover:text-gov-blue-600">
              {item.label}
            </Link>
          ) : (
            <span className="text-gov-gray-900">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
