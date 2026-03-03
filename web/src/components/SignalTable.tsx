"use client";

import { useRouter } from "next/navigation";
import { severityColor, formatDate } from "@/lib/utils";
import { SEVERITY_LABELS } from "@/lib/constants";
import type { RiskSignal } from "@/lib/types";
import {
  AlertCircle,
  AlertTriangle,
  Info,
  ShieldAlert,
  Calendar,
  TrendingUp,
  Clock,
} from "lucide-react";

interface SignalTableProps {
  signals: RiskSignal[];
}

const SEVERITY_ICONS = {
  low: Info,
  medium: AlertCircle,
  high: AlertTriangle,
  critical: ShieldAlert,
} as const;

export function SignalTable({ signals }: SignalTableProps) {
  const router = useRouter();

  return (
    <>
      <div className="space-y-3 md:hidden">
        {signals.map((signal) => {
          const SevIcon = SEVERITY_ICONS[signal.severity];
          const confidence = Math.round(signal.confidence * 100);
          return (
            <div
              key={signal.id}
              role="button"
              tabIndex={0}
              onClick={() => router.push(`/signal/${signal.id}`)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  router.push(`/signal/${signal.id}`);
                }
              }}
              className="w-full rounded-xl border border-gov-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-gov-blue-300 hover:bg-gov-blue-50"
            >
              <div className="flex items-start justify-between gap-2">
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${severityColor(signal.severity)}`}
                >
                  <SevIcon className="h-3 w-3" />
                  {SEVERITY_LABELS[signal.severity]}
                </span>
                <span className="rounded-full bg-gov-blue-100 px-2 py-0.5 font-mono text-xs font-semibold text-gov-blue-700">
                  {signal.typology_code}
                </span>
              </div>

              <h3 className="mt-3 text-sm font-semibold text-gov-gray-900">
                {signal.title}
              </h3>

              <div className="mt-3 flex items-center gap-2">
                <div className="h-2 flex-1 rounded-full bg-gov-gray-200">
                  <div
                    className="h-2 rounded-full bg-gov-blue-600"
                    style={{ width: `${confidence}%` }}
                  />
                </div>
                <span className="text-xs font-medium text-gov-gray-600">
                  {confidence}%
                </span>
              </div>

              <div className="mt-3 flex flex-col gap-1 text-xs text-gov-gray-500">
                {(signal.period_start || signal.period_end) && (
                  <span className="inline-flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    Analise: {signal.period_start ? formatDate(signal.period_start) : "---"}
                    {" → "}
                    {signal.period_end ? formatDate(signal.period_end) : "---"}
                  </span>
                )}
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  Ingestao: {formatDate(signal.created_at)}
                </span>
              </div>
              {signal.event_ids.length > 0 && (
                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      router.push(`/signal/${signal.id}/graph`);
                    }}
                    className="rounded-md border border-gov-blue-200 bg-gov-blue-50 px-2.5 py-1 text-xs font-medium text-gov-blue-700 transition hover:bg-gov-blue-100"
                  >
                    Ver teia
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="hidden overflow-x-auto rounded-xl border border-gov-gray-200 bg-white shadow-sm md:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gov-gray-200 bg-gov-gray-50">
            <tr>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
                Severidade
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
                Tipologia
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
                Titulo
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
                <span className="inline-flex items-center gap-1">
                  <TrendingUp className="h-3.5 w-3.5" />
                  Confianca
                </span>
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
                <span className="inline-flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  Periodo de Analise
                </span>
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  Ingestao
                </span>
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gov-gray-500">
                Acoes
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gov-gray-100">
            {signals.map((signal) => {
              const SevIcon = SEVERITY_ICONS[signal.severity];
              const confidence = Math.round(signal.confidence * 100);
              return (
                <tr
                  key={signal.id}
                  onClick={() => router.push(`/signal/${signal.id}`)}
                  className="cursor-pointer transition-colors hover:bg-gov-blue-50"
                >
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${severityColor(signal.severity)}`}
                    >
                      <SevIcon className="h-3 w-3" />
                      {SEVERITY_LABELS[signal.severity]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-gov-blue-100 px-2 py-0.5 font-mono text-xs font-semibold text-gov-blue-700">
                      {signal.typology_code}
                    </span>
                  </td>
                  <td className="max-w-[28rem] px-4 py-3 font-medium text-gov-gray-900">
                    {signal.title}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-20 rounded-full bg-gov-gray-200">
                        <div
                          className="h-2 rounded-full bg-gov-blue-600 transition-all"
                          style={{ width: `${confidence}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gov-gray-500">
                        {confidence}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gov-gray-500">
                    {signal.period_start || signal.period_end ? (
                      <span>
                        {signal.period_start ? formatDate(signal.period_start) : "---"}
                        {" → "}
                        {signal.period_end ? formatDate(signal.period_end) : "---"}
                      </span>
                    ) : (
                      <span className="text-gov-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gov-gray-500">
                    {formatDate(signal.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    {signal.event_ids.length > 0 ? (
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          router.push(`/signal/${signal.id}/graph`);
                        }}
                        className="rounded-md border border-gov-blue-200 bg-gov-blue-50 px-2.5 py-1 text-xs font-medium text-gov-blue-700 transition hover:bg-gov-blue-100"
                      >
                        Ver teia
                      </button>
                    ) : (
                      <span className="text-xs text-gov-gray-300">Sem teia</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
