"use client";

import Link from "next/link";
import { Building2, User, Landmark } from "lucide-react";
import type { EntitySearchResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";

const TYPE_CONFIG: Record<string, { label: string; icon: typeof Building2; color: string }> = {
  company: { label: "Empresa", icon: Building2, color: "bg-emerald-500/10 text-emerald-600" },
  person: { label: "Pessoa", icon: User, color: "bg-blue-500/10 text-blue-600" },
  org: { label: "Orgao", icon: Landmark, color: "bg-violet-500/10 text-violet-600" },
};

interface EntityResultCardProps {
  entity: EntitySearchResult;
}

export function EntityResultCard({ entity }: EntityResultCardProps) {
  const config = TYPE_CONFIG[entity.type] ?? TYPE_CONFIG.company;
  const Icon = config.icon;
  const cnpj = entity.identifiers?.cnpj || entity.identifiers?.cpf;

  return (
    <Link
      href={`/entity/${entity.id}`}
      className="group flex items-start gap-3 rounded-xl border border-border bg-surface-card p-4 transition-all duration-120 hover:shadow-sm hover:border-accent/30"
    >
      <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", config.color)}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-primary group-hover:text-accent transition-colors truncate">
          {entity.name}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", config.color)}>
            {config.label}
          </span>
          {cnpj && (
            <span className="font-mono text-[10px] text-muted">{cnpj}</span>
          )}
        </div>
        {entity.cluster_id && (
          <p className="mt-1 font-mono text-[10px] text-muted truncate">
            Cluster: {entity.cluster_id.slice(0, 8)}...
          </p>
        )}
        <ConfidenceBadge score={entity.cluster_confidence} />
      </div>
    </Link>
  );
}
