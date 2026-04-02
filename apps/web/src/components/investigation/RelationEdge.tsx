"use client";

import { memo, useState } from "react";
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from "@xyflow/react";
import { getTokens } from "@/lib/design-tokens";
import type { EdgeContext } from "@/hooks/useCaseGraph";

const EDGE_LABELS: Record<string, string> = {
  contrato: "Contrato",
  socio: "Socio",
  socio_controlador: "Controlador",
  socio_oculto: "Socio Oculto",
  representante_legal: "Repr. Legal",
  servidor: "Servidor",
  ex_servidor: "Ex-Servidor",
  subcontratacao: "Subcontratacao",
  vinculo_familiar: "Vinculo Familiar",
  presidente: "Presidente",
  diretor: "Diretor",
  conselheiro: "Conselheiro",
  fiscalizacao: "Fiscalizacao",
  doacao: "Doacao",
  consorcio: "Consorcio",
};


function RelationEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  style,
}: EdgeProps) {
  const [hovered, setHovered] = useState(false);
  const t = getTokens();

  const edgeType = (data?.type as string) ?? "";
  const weight = (data?.weight as number) ?? 1;
  const isFocused = Boolean(data?.isFocused);
  const edgeStrength = (data?.edge_strength as string) ?? "weak";
  const context = data?.context as EdgeContext | undefined;
  const label = EDGE_LABELS[edgeType] ?? edgeType.replace(/_/g, " ");
  const isDashed = edgeType === "socio_oculto" || edgeType === "vinculo_familiar";

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    curvature: 0.25,
  });

  // Invisible wider hit area for hover detection
  const hitAreaStyle: React.CSSProperties = {
    stroke: "transparent",
    strokeWidth: 16,
    fill: "none",
    cursor: "pointer",
  };

  return (
    <>
      {/* Hit area (invisible, wider stroke for easy hover) */}
      <path
        d={edgePath}
        style={hitAreaStyle}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />

      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: selected ? t.accent : t.border,
          strokeWidth: selected
            ? 1.5
            : isFocused
              ? Math.max(1.5, weight + 0.5)
              : Math.max(edgeStrength === "strong" ? 1.5 : 1, weight),
          opacity: selected ? 1 : isFocused ? 0.9 : edgeStrength === "strong" ? 0.7 : 0.45,
          strokeDasharray: isDashed ? "6 3" : undefined,
          transition: "stroke 150ms, opacity 150ms, stroke-width 150ms",
          pointerEvents: "none",
        }}
        markerEnd={`url(#arrow-${selected || isFocused ? "selected" : "default"})`}
      />

      {/* Label: only visible on hover or when selected */}
      {(hovered || selected) && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan pointer-events-auto absolute"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
          >
            {hovered && context ? (
              <div className="w-56 rounded-lg border border-border bg-surface-card p-3 shadow-lg">
                <span className="mb-2 inline-block rounded-full border border-accent-subtle bg-accent-subtle px-2 py-0.5 text-[9px] font-semibold leading-none text-accent">
                  {label}
                </span>
                <div className="mt-1.5 space-y-1.5 text-[10px]">
                  <p className="font-mono text-secondary">
                    <span className="text-muted">Eventos em comum:</span>{" "}
                    {context.sharedEventCount}
                  </p>
                  {context.totalValueBrl > 0 && (
                    <p className="font-mono text-secondary">
                      <span className="text-muted">Valor total:</span>{" "}
                      {context.totalValueBrl.toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                      })}
                    </p>
                  )}
                  {context.dateRange && (
                    <p className="font-mono text-secondary">
                      <span className="text-muted">Periodo:</span>{" "}
                      {context.dateRange.earliest.slice(0, 10)} —{" "}
                      {context.dateRange.latest.slice(0, 10)}
                    </p>
                  )}
                  {context.topEvents.length > 0 && (
                    <div className="mt-1 border-t border-border pt-1.5">
                      {context.topEvents.map((ev, i) => (
                        <div key={i} className="mb-1 last:mb-0">
                          <p className="line-clamp-1 text-primary">
                            {ev.description}
                          </p>
                          <p className="text-muted">
                            {ev.occurred_at.slice(0, 10)}
                            {ev.value_brl != null &&
                              ` · ${ev.value_brl.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}`}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <span className="bg-surface-card text-[10px] px-1 border border-border inline-block text-muted">
                {label}
              </span>
            )}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export const RelationEdge = memo(RelationEdgeComponent);
