"use client";

import { memo, useMemo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { User, Building2, Landmark } from "lucide-react";
import { cn } from "@/lib/utils";

/** Read CSS variable at runtime */
function getCSSToken(varName: string): string {
  if (typeof document === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

/** Build TYPE_CONFIG dynamically using CSS variables */
function buildTypeConfig(): Record<
  string,
  { Icon: typeof User; label: string; accent: string; iconBg: string }
> {
  const getAccent = (type: string): string => {
    const tokenMap: Record<string, string> = {
      person: "--color-entity-person",
      company: "--color-entity-company",
      org: "--color-entity-org",
    };
    const token = tokenMap[type];
    return token ? getCSSToken(token) : getCSSToken("--color-muted");
  };

  const computeIconBg = (accentColor: string): string => {
    // Parse hex color to create rgba version with transparency
    if (!accentColor) return "rgba(82, 82, 160, 0.12)";
    try {
      const hex = accentColor.trim();
      if (!hex.startsWith("#")) return "rgba(82, 82, 160, 0.12)";
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return `rgba(${r},${g},${b},0.12)`;
    } catch {
      return "rgba(82, 82, 160, 0.12)";
    }
  };

  return {
    person: {
      Icon: User,
      label: "Pessoa",
      accent: getAccent("person"),
      iconBg: computeIconBg(getAccent("person")),
    },
    company: {
      Icon: Building2,
      label: "Empresa",
      accent: getAccent("company"),
      iconBg: computeIconBg(getAccent("company")),
    },
    org: {
      Icon: Landmark,
      label: "Órgão",
      accent: getAccent("org"),
      iconBg: computeIconBg(getAccent("org")),
    },
  };
}

const SEVERITY_BORDER: Record<string, string> = {
  critical: "var(--color-critical)",
  high: "var(--color-high)",
  medium: "var(--color-medium)",
  low: "var(--color-low)",
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
  const typeConfig = useMemo(() => buildTypeConfig(), []);
  const config = typeConfig[nodeData.nodeType] ?? typeConfig.person;
  const { Icon } = config;

  const severityColor = nodeData.severity ? (SEVERITY_BORDER[nodeData.severity] ?? "var(--color-border)") : "var(--color-border)";

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0 !w-2 !h-2" />

      <div
        className={cn(
          "relative flex items-center gap-2.5 transition-shadow duration-150",
          selected
            ? "shadow-lg ring-2 ring-accent/20"
            : nodeData.isFocused
              ? "shadow-md ring-2 ring-accent/20"
              : "shadow-sm hover:shadow-md",
        )}
        style={{
          minWidth: 172,
          maxWidth: 240,
          background: "var(--color-bg)",
          border: `1px solid var(--color-border)`,
          borderLeft: `2px solid ${severityColor}`,
        }}
      >
        <div className="flex items-center gap-2 py-2 pl-3.5 pr-3">
          {/* Icon circle */}
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center"
            style={{ background: config.iconBg }}
          >
            <Icon className="h-3.5 w-3.5" style={{ color: config.accent }} strokeWidth={2.2} />
          </div>

          {/* Text */}
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-semibold text-primary leading-tight">
              {nodeData.label}
            </p>
            <div className="mt-px flex items-center gap-1">
              <span className="text-[9px] font-medium opacity-80" style={{ color: config.accent }}>
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
            <span className="flex h-4 min-w-4 shrink-0 items-center justify-center bg-surface-subtle px-1 text-[9px] font-semibold text-muted">
              {nodeData.connectionCount}
            </span>
          )}
        </div>

        {nodeData.isFocused && (
          <span
            className="absolute -bottom-1 -right-1 px-1.5 py-0.5 text-[8px] font-semibold"
            style={{ background: "var(--color-warning)", color: "var(--color-bg)" }}
          >
            foco
          </span>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-2 !h-2" />
    </>
  );
}

export const EntityNode = memo(EntityNodeComponent);
