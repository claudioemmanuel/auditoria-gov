import { clsx } from "clsx";
import { isValidElement } from "react";
import type { ReactNode, ElementType } from "react";

type IconComponent = ElementType<{ size?: number; className?: string }>;
type IconProp = ReactNode | IconComponent;

interface EmptyStateProps {
  icon?: IconProp;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

function renderIcon(icon: IconProp) {
  if (!icon) return null;
  if (isValidElement(icon)) return icon;

  if (
    typeof icon === "function" ||
    (typeof icon === "object" && icon !== null && "$$typeof" in icon)
  ) {
    const Icon = icon as IconComponent;
    return <Icon size={32} className="text-[var(--color-text-3)]" />;
  }

  if (typeof icon === "string" || typeof icon === "number") {
    return icon;
  }

  return null;
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
