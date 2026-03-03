"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { User, Building2, Landmark } from "lucide-react";

const TYPE_CONFIG: Record<
  string,
  { Icon: typeof User; label: string; accent: string; bg: string; border: string; iconBg: string; accentBar: string }
> = {
  person: {
    Icon: User,
    label: "Pessoa",
    accent: "text-blue-600",
    bg: "bg-white",
    border: "border-gray-200",
    iconBg: "bg-blue-50",
    accentBar: "bg-blue-500",
  },
  company: {
    Icon: Building2,
    label: "Empresa",
    accent: "text-emerald-600",
    bg: "bg-white",
    border: "border-gray-200",
    iconBg: "bg-emerald-50",
    accentBar: "bg-emerald-500",
  },
  org: {
    Icon: Landmark,
    label: "Orgao",
    accent: "text-violet-600",
    bg: "bg-white",
    border: "border-gray-200",
    iconBg: "bg-violet-50",
    accentBar: "bg-violet-500",
  },
};

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-amber-400",
  low: "bg-blue-400",
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
        className={`
          relative flex items-center gap-2.5 rounded-lg border overflow-hidden
          transition-shadow duration-150
          ${config.bg} ${config.border}
          ${selected
            ? "shadow-lg ring-2 ring-gov-blue-500/40 border-gov-blue-400"
            : nodeData.isFocused
              ? "shadow-md ring-2 ring-amber-400/50 border-amber-300"
              : "shadow-sm hover:shadow-md"
          }
        `}
        style={{ minWidth: 172, maxWidth: 240 }}
      >
        {/* Left accent bar */}
        <div className={`absolute left-0 top-0 bottom-0 w-1 ${config.accentBar} ${nodeData.isSeed ? "opacity-100" : "opacity-40"}`} />

        <div className="flex items-center gap-2 py-2 pl-3.5 pr-3">
          {/* Icon circle */}
          <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${config.iconBg}`}>
            <Icon className={`h-3.5 w-3.5 ${config.accent}`} strokeWidth={2.2} />
          </div>

          {/* Text */}
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-semibold text-gray-800 leading-tight">
              {nodeData.label}
            </p>
            <div className="flex items-center gap-1 mt-px">
              <span className={`text-[9px] font-medium ${config.accent} opacity-80`}>
                {config.label}
              </span>
              {nodeData.identifier && (
                <>
                  <span className="text-gray-300 text-[8px]">/</span>
                  <span className="text-[9px] font-mono text-gray-400 truncate">
                    {nodeData.identifier}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Connection count */}
          {nodeData.connectionCount != null && nodeData.connectionCount > 0 && (
            <span className="shrink-0 flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-gray-100 px-1 text-[9px] font-semibold text-gray-500">
              {nodeData.connectionCount}
            </span>
          )}
        </div>

        {/* Severity indicator for seeds */}
        {nodeData.isSeed && nodeData.severity && (
          <div
            className={`absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-[1.5px] border-white ${
              SEVERITY_DOT[nodeData.severity] ?? SEVERITY_DOT.low
            }`}
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
