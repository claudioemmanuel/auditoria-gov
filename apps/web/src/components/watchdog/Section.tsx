// apps/web/src/components/watchdog/Section.tsx
import type { ReactNode } from "react";
import clsx from "clsx";

export interface SectionProps {
  title: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function Section({ title, children, action, className }: SectionProps) {
  return (
    <section className={clsx("space-y-4", className)}>
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-base font-medium text-[var(--color-text)]">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
