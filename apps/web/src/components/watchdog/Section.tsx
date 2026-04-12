// apps/web/src/components/watchdog/Section.tsx

export interface SectionProps {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}

export function Section({ title, children, action }: SectionProps) {
  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-base font-medium text-[var(--color-text)]">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
