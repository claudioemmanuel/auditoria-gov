"use client";

import { useRouter } from "next/navigation";
import type { RadarV2SignalItem } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";

interface RadarSignalsListProps {
  items: RadarV2SignalItem[];
  onOpenPreview: (signalId: string) => void;
}

export function RadarSignalsList({ items, onOpenPreview }: RadarSignalsListProps) {
  const router = useRouter();

  return (
    <div className="overflow-x-auto rounded-xl border border-gov-gray-200 bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-gov-gray-200 bg-gov-gray-50">
          <tr>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Severidade</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Tipologia</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Titulo</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Confianca</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Periodo</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Eventos</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">Acoes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gov-gray-100">
          {items.map((signal) => (
            <tr
              key={signal.id}
              onClick={() => router.push(`/signal/${signal.id}`)}
              className="cursor-pointer transition-colors hover:bg-gov-blue-50"
            >
              <td className="px-4 py-3 text-xs font-medium text-gov-gray-700">
                {SEVERITY_LABELS[signal.severity]}
              </td>
              <td className="px-4 py-3 text-xs text-gov-gray-600">
                {signal.typology_code} - {signal.typology_name}
              </td>
              <td className="max-w-[30rem] px-4 py-3 font-medium text-gov-gray-900">
                {signal.title}
              </td>
              <td className="px-4 py-3 text-xs text-gov-gray-600">
                {Math.round(signal.confidence * 100)}%
              </td>
              <td className="px-4 py-3 text-xs text-gov-gray-500">
                {(signal.period_start || signal.period_end)
                  ? `${signal.period_start ? formatDate(signal.period_start) : "---"} -> ${signal.period_end ? formatDate(signal.period_end) : "---"}`
                  : "Nao informado"}
              </td>
              <td className="px-4 py-3 text-xs text-gov-gray-500">
                {signal.event_count} eventos / {signal.entity_count} entidades
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onOpenPreview(signal.id);
                    }}
                    className="rounded-md border border-gov-blue-200 bg-gov-blue-50 px-2.5 py-1 text-xs font-medium text-gov-blue-700 hover:bg-gov-blue-100"
                  >
                    Previa
                  </button>
                  {signal.has_graph && (
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        router.push(`/signal/${signal.id}/graph`);
                      }}
                      className="rounded-md border border-gov-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gov-gray-700 hover:bg-gov-gray-50"
                    >
                      Ver teia
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
