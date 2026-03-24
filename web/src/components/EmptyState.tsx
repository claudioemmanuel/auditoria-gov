import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center py-12",
        className,
      )}
    >
      <div className="flex h-14 w-14 items-center justify-center border border-border bg-surface-subtle">
        <Icon className="h-7 w-7 text-muted" />
      </div>
      <h3 className="mt-4 text-base font-medium text-muted">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-center text-sm text-secondary">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
