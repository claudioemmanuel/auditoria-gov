import { AlertTriangle, AlertCircle } from "lucide-react";

interface ConfidenceBadgeProps {
  score: number | null | undefined;
}

/**
 * Renders a warning badge when ER cluster confidence is below 80.
 * - score >= 80 or null/undefined: no badge (high confidence or unmerged entity)
 * - score 60–79: amber warning (partial confidence)
 * - score < 60: red warning (insufficient confidence — data shown for analysis only)
 */
export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  if (score == null || score >= 80) return null;

  if (score >= 60) {
    return (
      <span className="inline-flex items-center gap-1 rounded-[4px] border border-amber/30 bg-amber-subtle px-2 py-0.5 font-mono text-[10px] font-medium text-amber">
        <AlertTriangle className="h-3 w-3 shrink-0" />
        Identidade com confiança parcial — verifique os dados de origem
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-[4px] border border-error/30 bg-error-subtle px-2 py-0.5 font-mono text-[10px] font-medium text-error">
      <AlertCircle className="h-3 w-3 shrink-0" />
      Confiança insuficiente — dado disponível para análise, não para afirmação
    </span>
  );
}
