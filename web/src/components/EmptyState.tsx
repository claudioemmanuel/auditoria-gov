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
    <div className="flex flex-col items-center justify-center rounded-lg border border-gov-gray-200 bg-white py-16">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gov-gray-100">
        <Icon className="h-7 w-7 text-gov-gray-400" />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-gov-gray-900">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-center text-sm text-gov-gray-500">
          {description}
        </p>
      )}
    </div>
  );
}
