"use client";

import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { RadarBreadcrumb } from "@/components/radar/RadarBreadcrumb";

// Lazy-load graph components — only compiled when user navigates here
const EntityNetworkGraph = dynamic(
  () => import("@/components/EntityNetworkGraph").then((m) => ({ default: m.EntityNetworkGraph })),
  { loading: () => <div className="h-96 animate-pulse bg-surface-subtle rounded-xl" />, ssr: false },
);

const PathFinder = dynamic(
  () => import("@/components/investigation-v2/PathFinder").then((m) => ({ default: m.PathFinder })),
  { loading: () => <div className="h-32 animate-pulse bg-surface-subtle rounded-xl" />, ssr: false },
);

export default function EntityNetworkPage() {
  const { entityId } = useParams<{ entityId: string }>();

  return (
    <div className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-6">
      <RadarBreadcrumb crumbs={[
        { label: "Radar", href: "/radar" },
        { label: "Rede", href: "/radar/rede" },
        { label: entityId?.slice(0, 8) ?? "Entidade" },
      ]} />

      <div className="mt-6 space-y-8">
        {/* Network graph */}
        <div className="rounded-xl border border-border bg-surface-card p-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted mb-3">
            Grafo de vizinhanca
          </p>
          {entityId && <EntityNetworkGraph entityId={entityId} />}
        </div>

        {/* Path finder */}
        <div className="rounded-xl border border-border bg-surface-card p-5">
          {entityId && <PathFinder initialSourceId={entityId} />}
        </div>
      </div>
    </div>
  );
}
