import { clsx } from "clsx";
import type { ReactNode, ComponentType } from "react";

type IconProp = ReactNode | ComponentType<{ size?: number; className?: string }>;

interface EmptyStateProps {
  icon?: IconProp;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

function renderIcon(icon: IconProp) {
  if (!icon) return null;
  if (typeof icon === "function") {
    const Icon = icon as ComponentType<{ size?: number; className?: string }>;
    return <Icon size={32} className="text-[var(--color-text-3)]" />;
  }
  return icon;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={clsx("ow-empty", className)}>
      {icon && <div className="ow-empty-icon">{renderIcon(icon)}</div>}
      <p className="ow-empty-title">{title}</p>
      {description && <p className="ow-empty-desc">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
