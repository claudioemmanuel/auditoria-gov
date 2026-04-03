import type { LegalHypothesis } from "@/lib/types";

interface Props {
  hypotheses: LegalHypothesis[];
}

export function LegalInferencePanel({ hypotheses }: Props) {
  if (hypotheses.length === 0) {
    return null;
  }

  return (
    <section className="mt-6">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
        Hipóteses de Violação Legal
      </h3>
      <div className="space-y-2">
        {hypotheses.map((h) => (
          <div key={h.id} className="flex items-start gap-3 rounded-md border p-3 text-sm">
            <div className="flex-1">
              <span className="font-medium">{h.law_name}</span>
              {h.article && <span className="text-muted-foreground ml-1">— {h.article}</span>}
              {h.violation_type && (
                <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-xs">
                  {h.violation_type}
                </span>
              )}
              {h.signal_cluster.length > 0 && (
                <div className="mt-1 text-xs text-muted-foreground">
                  Sinais: {h.signal_cluster.join(', ')}
                </div>
              )}
            </div>
            <div className="text-right text-xs text-muted-foreground whitespace-nowrap">
              {Math.round(h.confidence * 100)}% conf.
            </div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-muted-foreground italic">
        ⚠️ Hipótese analítica — não constitui conclusão jurídica.
      </p>
    </section>
  );
}
