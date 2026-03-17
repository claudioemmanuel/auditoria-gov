"use client";

import { useEffect, useState } from "react";
import { getRadarV2Summary } from "@/lib/api";
import type { RadarV2SummaryResponse } from "@/lib/types";
import { RadarBreadcrumb } from "@/components/radar/RadarBreadcrumb";
import { LegalSection } from "@/components/investigation-v2/LegalSection";
import { TableSkeleton } from "@/components/Skeleton";

export default function JuridicoPage() {
  const [summary, setSummary] = useState<RadarV2SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRadarV2Summary()
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-6">
      <RadarBreadcrumb crumbs={[
        { label: "Radar", href: "/radar" },
        { label: "Juridico" },
      ]} />

      <div className="mt-6">
        {loading && <TableSkeleton rows={6} />}
        {!loading && (
          <LegalSection typologyCounts={summary?.typology_counts ?? []} />
        )}
      </div>
    </div>
  );
}
