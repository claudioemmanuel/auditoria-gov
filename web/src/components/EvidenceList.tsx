import Link from "next/link";
import type { EvidenceRef } from "@/lib/types";
import { FileText, ExternalLink, Layers, Building2, FileSearch } from "lucide-react";

interface EvidenceListProps {
  refs: EvidenceRef[];
}

const REF_TYPE_CONFIG: Record<string, { label: string; icon: typeof FileText }> = {
  event: { label: "Evento", icon: FileText },
  baseline: { label: "Baseline", icon: Layers },
  entity: { label: "Entidade", icon: Building2 },
  external_url: { label: "Fonte externa", icon: ExternalLink },
  raw_source: { label: "Registro bruto", icon: FileSearch },
};

export function EvidenceList({ refs }: EvidenceListProps) {
  if (refs.length === 0) return null;

  return (
    <div>
      <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase text-gov-gray-500">
        <FileText className="h-3.5 w-3.5" />
        Evidencias ({refs.length})
      </h4>
      <ul className="mt-2 space-y-2">
        {refs.map((ref, i) => {
          const config = REF_TYPE_CONFIG[ref.ref_type] || { label: ref.ref_type, icon: FileText };
          const RefIcon = config.icon;
          return (
            <li key={i} className="rounded-md border border-gov-gray-100 bg-gov-gray-50 p-2">
              <div className="flex items-start gap-2">
                <RefIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gov-blue-500" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-gov-gray-700">{ref.description}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <span className="rounded bg-gov-gray-200 px-1 py-0.5 text-xs text-gov-gray-500">
                      {config.label}
                    </span>
                    {ref.url && (
                      <a
                        href={ref.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-0.5 text-xs text-gov-blue-600 underline hover:text-gov-blue-800"
                      >
                        fonte
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                    {ref.ref_id && ref.ref_type === "entity" && (
                      <Link
                        href={`/entity/${ref.ref_id}`}
                        className="inline-flex items-center gap-0.5 text-xs text-gov-blue-600 underline hover:text-gov-blue-800"
                      >
                        ver entidade
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
