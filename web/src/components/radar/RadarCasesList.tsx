"use client";

import { useRouter } from "next/navigation";
import type { RadarV2CaseItem } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { SEVERITY_LABELS, TYPOLOGY_LABELS } from "@/lib/constants";

interface RadarCasesListProps {
  items: RadarV2CaseItem[];
  onOpenPreview: (caseId: string) => void;
}

export function RadarCasesList({ items, onOpenPreview }: RadarCasesListProps) {
  const router = useRouter();

  return (
    <div className="overflow-x-auto rounded-xl border border-gov-gray-200 bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-gov-gray-200 bg-gov-gray-50">
          <tr>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Severidade</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Caso</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Resumo</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Tipologias</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Periodo</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Acoes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gov-gray-100">
          {items.map((item) => (
            <tr
              key={item.id}
              onClick={() => router.push(`/case/${item.id}`)}
              className="cursor-pointer transition-colors hover:bg-gov-blue-50"
            >
              <td className="px-4 py-3 text-xs font-medium text-gov-gray-700">
                {SEVERITY_LABELS[item.severity]}
              </td>
              <td className="px-4 py-3">
                <p className="font-medium text-gov-gray-900">{item.title}</p>
                <p className="text-xs text-gov-gray-500">
                  {item.signal_count} sinais / {item.entity_count} entidades
                </p>
              </td>
              <td className="max-w-[24rem] px-4 py-3 text-xs text-gov-gray-600">
                {item.summary || "Sem resumo"}
              </td>
              <td className="px-4 py-3 text-xs text-gov-gray-600">
                {item.typology_codes.length > 0
                  ? item.typology_codes
                    .map((code) => TYPOLOGY_LABELS[code] ?? code)
                    .join(", ")
                  : "Nao informado"}
              </td>
              <td className="px-4 py-3 text-xs text-gov-gray-500">
                {(item.period_start || item.period_end)
                  ? `${item.period_start ? formatDate(item.period_start) : "---"} -> ${item.period_end ? formatDate(item.period_end) : "---"}`
                  : formatDate(item.created_at)}
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onOpenPreview(item.id);
                    }}
                    className="rounded-md border border-gov-blue-200 bg-gov-blue-50 px-2.5 py-1 text-xs font-medium text-gov-blue-700 hover:bg-gov-blue-100"
                  >
                    Previa
                  </button>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      router.push(`/investigation/${item.id}`);
                    }}
                    className="rounded-md border border-gov-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gov-gray-700 hover:bg-gov-gray-50"
                  >
                    Investigar
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
