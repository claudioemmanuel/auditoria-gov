"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { User, Building2, Landmark } from "lucide-react";
import { cn } from "@/lib/utils";

const TYPE_CONFIG: Record<
  string,
  { Icon: typeof User; label: string; accent: string; iconBg: string; accentBar: string }
> = {
  person: {
    Icon: User,
    label: "Pessoa",
    accent: "text-blue-600",
    iconBg: "bg-blue-50",
    accentBar: "bg-blue-500",
  },
  company: {
    Icon: Building2,
    label: "Empresa",
    accent: "text-emerald-600",
    iconBg: "bg-emerald-50",
    accentBar: "bg-emerald-500",
  },
  org: {
    Icon: Landmark,
    label: "Órgão",
    accent: "text-violet-600",
    iconBg: "bg-violet-50",
    accentBar: "bg-violet-500",
  },
};

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
};

export interface EntityNodeData {
  label: string;
  nodeType: string;
  entityId: string;
  isSeed: boolean;
  isFocused?: boolean;
  severity?: string;
  identifier?: string;
  connectionCount?: number;
  [key: string]: unknown;
}

function EntityNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as EntityNodeData;
  const config = TYPE_CONFIG[nodeData.nodeType] ?? TYPE_CONFIG.person;
  const { Icon } = config;

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0 !w-2 !h-2" />

      <div
        className={cn(
          "relative flex items-center gap-2.5 rounded-lg border overflow-hidden transition-shadow duration-150 bg-surface-card",
          selected
            ? "border-accent shadow-lg ring-2 ring-accent/20 bg-accent-subtle/10"
            : nodeData.isFocused
              ? "border-amber-300 shadow-md ring-2 ring-amber-400/50"
              : "border-border shadow-sm hover:shadow-md",
        )}
        style={{ minWidth: 172, maxWidth: 240 }}
      >
        {/* Left accent bar */}
        <div
          className={cn(
            "absolute left-0 top-0 bottom-0 w-1",
            config.accentBar,
            nodeData.isSeed ? "opacity-100" : "opacity-40",
          )}
        />

        <div className="flex items-center gap-2 py-2 pl-3.5 pr-3">
          {/* Icon circle */}
          <div className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-full", config.iconBg)}>
            <Icon className={cn("h-3.5 w-3.5", config.accent)} strokeWidth={2.2} />
          </div>

          {/* Text */}
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-semibold text-primary leading-tight">
              {nodeData.label}
            </p>
            <div className="mt-px flex items-center gap-1">
              <span className={cn("text-[9px] font-medium opacity-80", config.accent)}>
                {config.label}
              </span>
              {nodeData.identifier && (
                <>
                  <span className="text-[8px] text-muted">/</span>
                  <span className="truncate text-[9px] font-mono tabular-nums text-muted">
                    {nodeData.identifier}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Connection count */}
          {nodeData.connectionCount != null && nodeData.connectionCount > 0 && (
            <span className="flex h-4 min-w-4 shrink-0 items-center justify-center rounded-full bg-surface-subtle px-1 text-[9px] font-semibold text-muted">
              {nodeData.connectionCount}
            </span>
          )}
        </div>

        {/* Severity dot for seeds */}
        {nodeData.isSeed && nodeData.severity && (
          <div
            className={cn(
              "absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-[1.5px] border-white",
              SEVERITY_DOT[nodeData.severity] ?? SEVERITY_DOT.low,
            )}
          />
        )}

        {nodeData.isFocused && (
          <span className="absolute -bottom-1 -right-1 rounded bg-amber-100 px-1.5 py-0.5 text-[8px] font-semibold text-amber-700">
            foco
          </span>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-2 !h-2" />
    </>
  );
}

export const EntityNode = memo(EntityNodeComponent);
