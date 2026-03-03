"use client";

import { memo, useState } from "react";
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from "@xyflow/react";
import { tokens } from "@/lib/design-tokens";

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

const EDGE_COLORS: Record<string, string> = {
  contrato: "#6366f1",
  socio: "#059669",
  socio_controlador: "#059669",
  socio_oculto: "#dc2626",
  representante_legal: "#059669",
  servidor: "#7c3aed",
  ex_servidor: "#9ca3af",
  subcontratacao: "#d97706",
  vinculo_familiar: "#ec4899",
  fiscalizacao: "#0284c7",
  doacao: "#ca8a04",
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

  const edgeType = (data?.type as string) ?? "";
  const weight = (data?.weight as number) ?? 1;
  const isFocused = Boolean(data?.isFocused);
  const edgeStrength = (data?.edge_strength as string) ?? "weak";
  const baseColor = EDGE_COLORS[edgeType] ?? "#94a3b8";
  const color = selected ? tokens.accent : isFocused ? "#1d4ed8" : baseColor;
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
          stroke: color,
          strokeWidth: selected
            ? 2.5
            : isFocused
              ? Math.max(2.2, weight + 0.5)
              : Math.max(edgeStrength === "strong" ? 2 : 1, weight),
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
            className="nodrag nopan pointer-events-none absolute"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            }}
          >
            <span className="rounded-full border border-accent-subtle bg-accent-subtle px-2 py-0.5 text-[9px] font-semibold leading-none text-accent shadow-sm">
              {label}
            </span>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export const RelationEdge = memo(RelationEdgeComponent);
