"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getEntity } from "@/lib/api";
import { GraphView } from "@/components/GraphView";
import { Breadcrumb } from "@/components/Breadcrumb";
import { DetailSkeleton } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { normalizeUnknownDisplay } from "@/lib/utils";
import type { EntityDetail } from "@/lib/types";
import {
  User,
  Building2,
  Landmark,
  Fingerprint,
  Users,
  GitBranch,
  AlertTriangle,
  Search,
} from "lucide-react";

const TYPE_ICONS = {
  person: User,
  company: Building2,
  org: Landmark,
} as const;

const TYPE_LABELS: Record<string, string> = {
  person: "Pessoa",
  company: "Empresa",
  org: "Orgao",
};

export default function EntityDetailPage() {
  const params = useParams();
  const [entity, setEntity] = useState<EntityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.id) {
      setLoading(true);
      setError(null);
      getEntity(params.id as string)
        .then(setEntity)
        .catch(() => setError("Erro ao carregar entidade"))
        .finally(() => setLoading(false));
    }
  }, [params.id]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <DetailSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <EmptyState
          icon={AlertTriangle}
          title="Erro ao carregar entidade"
          description={error}
        />
      </div>
    );
  }

  if (!entity) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <EmptyState
          icon={Search}
          title="Entidade nao encontrada"
          description="A entidade solicitada nao existe ou foi removida"
        />
      </div>
    );
  }

  const TypeIcon = TYPE_ICONS[entity.type as keyof typeof TYPE_ICONS] ?? User;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Breadcrumb
        items={[
          { label: "Radar", href: "/radar" },
          { label: entity.name },
        ]}
      />

      <div className="mt-4 flex items-start gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gov-blue-100">
          <TypeIcon className="h-6 w-6 text-gov-blue-700" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gov-gray-900">{entity.name}</h1>
          <div className="mt-0.5 flex items-center gap-3 text-sm text-gov-gray-500">
            <span>{TYPE_LABELS[entity.type] ?? normalizeUnknownDisplay(entity.type)}</span>
            {entity.cluster_id && (
              <span className="rounded bg-gov-gray-100 px-2 py-0.5 font-mono text-xs text-gov-gray-600">
                Cluster: {entity.cluster_id.slice(0, 8)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Identifiers */}
      {Object.keys(entity.identifiers).length > 0 && (
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Fingerprint className="h-5 w-5 text-gov-blue-600" />
            Identificadores
          </h2>
          <dl className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {Object.entries(entity.identifiers).map(([key, value]) => (
              <div key={key} className="rounded-lg bg-gov-gray-100 p-3">
                <dt className="text-xs font-medium uppercase text-gov-gray-500">
                  {key}
                </dt>
                <dd className="mt-0.5 font-mono text-sm text-gov-gray-900">
                  {normalizeUnknownDisplay(value)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Aliases */}
      {entity.aliases.length > 0 && (
        <div className="mt-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
            <Users className="h-5 w-5 text-gov-blue-600" />
            Nomes alternativos
          </h2>
          <ul className="mt-2 space-y-1">
            {entity.aliases.map((alias, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-gov-gray-700">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-gov-blue-400" />
                {alias.value}{" "}
                <span className="text-gov-gray-400">
                  ({normalizeUnknownDisplay(alias.type)}, fonte: {normalizeUnknownDisplay(alias.source)})
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Graph */}
      <div className="mt-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gov-gray-900">
          <GitBranch className="h-5 w-5 text-gov-blue-600" />
          Grafo de Relacionamentos
        </h2>
        <div className="mt-2 overflow-hidden rounded-lg border border-gov-gray-200 bg-white">
          <GraphView entityId={entity.id} />
        </div>
      </div>
    </div>
  );
}
