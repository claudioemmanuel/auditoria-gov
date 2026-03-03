import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-surface-card py-16">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-surface-subtle">
        <Icon className="h-7 w-7 text-muted" />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-primary">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-center text-sm text-secondary">
          {description}
        </p>
      )}
    </div>
  );
}
