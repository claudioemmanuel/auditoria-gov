import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface PageHeroProps {
  icon: LucideIcon;
  title: string;
  description: string;
  note: string;
  noteTitle?: string;
  aside?: ReactNode;
}

export function PageHero({
  icon: Icon,
  title,
  description,
  note,
  noteTitle = "Leitura obrigatória",
  aside,
}: PageHeroProps) {
  return (
    <section className="surface-card mt-4 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="rounded-xl border border-gov-blue-200 bg-gov-blue-50 p-2.5">
            <Icon className="h-6 w-6 text-gov-blue-700" />
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-gov-gray-900">{title}</h1>
            <p className="mt-2 max-w-4xl text-[0.96rem] leading-relaxed text-gov-gray-600">{description}</p>
          </div>
        </div>
        {aside}
      </div>

      <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-[0.95rem] text-amber-900">
        <strong>{noteTitle}:</strong> {note}
      </div>
    </section>
  );
}
