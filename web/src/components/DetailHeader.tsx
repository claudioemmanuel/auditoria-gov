import { Breadcrumb } from "@/components/Breadcrumb";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface DetailHeaderProps {
  breadcrumbs: BreadcrumbItem[];
  title: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
}

export function DetailHeader({ breadcrumbs, title, badge, actions }: DetailHeaderProps) {
  return (
    <div>
      <Breadcrumb items={breadcrumbs} />
      <div className="mt-2 flex items-start justify-between gap-4">
        <h1 className="font-display text-xl font-bold text-primary truncate sm:text-2xl">
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
