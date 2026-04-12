// apps/web/src/components/watchdog/CaseCard.tsx

import Link from "next/link";
import { SignalTag } from "./SignalTag";

export type RiskLevel = "CRÍTICO" | "ALTO" | "MÉDIO" | "BAIXO";

const RISK_COLORS: Record<RiskLevel, string> = {
  "CRÍTICO": "var(--color-critical)",
  "ALTO":    "var(--color-high)",
  "MÉDIO":   "var(--color-medium)",
  "BAIXO":   "var(--color-low)",
};

export interface CaseCardProps {
  id: string;
  riskLevel: RiskLevel;
  title: string;
  company: string;
  agency: string;
  signals: string[];
  explanation: string;
  flaggedAt: string;
}

export function CaseCard({
  id,
  riskLevel,
  title,
  company,
  agency,
  signals,
  explanation,
  flaggedAt,
}: CaseCardProps) {
  const riskColor = RISK_COLORS[riskLevel];

  return (
    <article className="border border-[var(--color-border)] rounded-lg p-5 space-y-4 bg-[var(--color-surface)]">
      {/* Risk level + timestamp */}
      <div className="flex items-center justify-between">
        <span
          className="text-xs font-semibold tracking-widest uppercase"
          style={{ color: riskColor }}
        >
          {riskLevel}
        </span>
        <span className="text-xs text-[var(--color-text-3)]">{flaggedAt}</span>
      </div>

      {/* Finding title */}
      <h3 className="text-base font-medium leading-snug text-[var(--color-text)]">
        {title}
      </h3>

      {/* Meta — monospace company ID, plain agency name */}
      <div className="space-y-2 text-sm">
        <div>
          <span className="label">Empresa</span>
          <br />
          <span className="data text-[var(--color-text-2)]">{company}</span>
        </div>
        <div>
          <span className="label">Órgão</span>
          <br />
          <span className="text-[var(--color-text-2)]">{agency}</span>
        </div>
      </div>

      {/* Signal tags */}
      <div className="flex flex-wrap gap-2">
        {signals.map((signal) => (
          <SignalTag key={signal} label={signal} />
        ))}
      </div>

      {/* Explanation — why this matters */}
      <p className="text-sm text-[var(--color-text-3)]">{explanation}</p>

      {/* Action */}
      <Link
        href={`/case/${id}`}
        className="text-sm font-medium text-[var(--color-brand-light)] hover:underline"
      >
        Ver detalhes →
      </Link>
    </article>
  );
}
