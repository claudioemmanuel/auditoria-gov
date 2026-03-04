"use client";

import type { PriceComparisonResult } from "@/lib/types";
import { formatBRL } from "@/lib/utils";
import { BarChart3, TrendingUp, Scale } from "lucide-react";

interface PriceResultsProps {
  result: PriceComparisonResult;
}

export function PriceResults({ result }: PriceResultsProps) {
  if (!result.baseline) {
    return (
      <div className="rounded-lg border border-border bg-surface-card p-6 text-center">
        <Scale className="mx-auto h-8 w-8 text-placeholder" />
        <h3 className="mt-3 text-sm font-semibold text-primary">
          Nenhum baseline disponivel
        </h3>
        <p className="mt-1 text-sm text-muted">
          {result.catmat_code
            ? `Nao ha dados suficientes de precos para o codigo "${result.catmat_code}". Os baselines sao calculados diariamente a partir dos dados ingeridos.`
            : "Informe um codigo CATMAT/CATSER para buscar baselines de precos."}
        </p>
      </div>
    );
  }

  const b = result.baseline;

  const stats = [
    { label: "Amostras", value: b.n.toLocaleString("pt-BR"), highlight: false },
    { label: "Media", value: formatBRL(b.mean), highlight: false },
    { label: "Mediana", value: formatBRL(b.median), highlight: false },
    { label: "Minimo", value: formatBRL(b.min), highlight: false },
    { label: "Maximo", value: formatBRL(b.max), highlight: false },
    { label: "Desvio padrão", value: formatBRL(b.std), highlight: false },
  ];

  const percentiles = [
    { label: "P10", value: formatBRL(b.p10), desc: "10% mais baratos" },
    { label: "P25", value: formatBRL(b.p25), desc: "25% mais baratos" },
    { label: "P75", value: formatBRL(b.p75), desc: "75% mais baratos" },
    { label: "P90", value: formatBRL(b.p90), desc: "Alerta alto" },
    { label: "P95", value: formatBRL(b.p95), desc: "Alerta critico" },
    { label: "P99", value: formatBRL(b.p99), desc: "Outlier extremo" },
  ];

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-surface-card p-6">
        <h3 className="flex items-center gap-2 font-semibold text-primary">
          <BarChart3 className="h-5 w-5 text-accent" />
          Baseline de Precos
          {result.catmat_code && (
            <span className="ml-2 rounded bg-accent-subtle px-2 py-0.5 font-mono text-xs text-accent">
              {result.catmat_code}
            </span>
          )}
        </h3>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {stats.map((s) => (
            <div key={s.label} className="rounded-lg bg-surface-base p-3 text-center">
              <p className="text-xs text-muted">{s.label}</p>
              <p className="mt-1 text-sm font-semibold text-primary">{s.value}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-border bg-surface-card p-6">
        <h3 className="flex items-center gap-2 font-semibold text-primary">
          <TrendingUp className="h-5 w-5 text-accent" />
          Distribuicao de Percentis
        </h3>
        <p className="mt-1 text-sm text-muted">
          Precos acima do P90 podem indicar sobrepreco. Acima do P95 sao sinalizados como criticos.
        </p>

        <div className="mt-4 space-y-2">
          {percentiles.map((p) => {
            const isAlert = p.label === "P90" || p.label === "P95" || p.label === "P99";
            return (
              <div
                key={p.label}
                className={`flex items-center justify-between rounded-md p-3 ${
                  isAlert ? "bg-severity-high-bg border border-severity-high/20" : "bg-surface-base"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded px-2 py-0.5 font-mono text-xs font-semibold ${
                      isAlert
                        ? "bg-severity-high-bg text-severity-high"
                        : "bg-surface-hover text-secondary"
                    }`}
                  >
                    {p.label}
                  </span>
                  <span className="text-sm text-secondary">{p.desc}</span>
                </div>
                <span className={`font-semibold ${isAlert ? "text-severity-high" : "text-primary"}`}>
                  {p.value}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
