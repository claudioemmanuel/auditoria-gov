import { Breadcrumb } from "@/components/Breadcrumb";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface DetailHeaderProps {
  breadcrumbs: BreadcrumbItem[];
  kicker?: string;
  title: string;
  titleClassName?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
}

export function DetailHeader({ breadcrumbs, kicker, title, titleClassName, badge, actions }: DetailHeaderProps) {
  return (
    <div>
      <Breadcrumb items={breadcrumbs} />
      {kicker && (
        <p className="section-kicker mt-2 mb-1">{kicker}</p>
      )}
      <div className="mt-2 flex items-start justify-between gap-4">
        <h1 className={`font-display text-xl font-bold text-primary truncate sm:text-2xl${titleClassName ? ` ${titleClassName}` : ""}`}>
          {title}
        </h1>
        {(badge || actions) && (
          <div className="flex shrink-0 items-center gap-2">
            {badge}
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}
