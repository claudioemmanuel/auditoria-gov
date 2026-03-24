import { cn } from "@/lib/utils";
import { Breadcrumb } from "@/components/Breadcrumb";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: React.ReactNode;
  border?: boolean;
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  breadcrumbs,
  actions,
  border = false,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "page-wrap pb-0",
        border && "pb-4",
        className,
      )}
    >
      {border && <div className="masthead-rule mb-4" />}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumb items={breadcrumbs} className="byline mb-3" />
      )}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-primary leading-snug">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-sm text-secondary leading-relaxed">{subtitle}</p>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        )}
      </div>
      {border && <div className="mt-4 h-px bg-border" />}
    </header>
  );
}
