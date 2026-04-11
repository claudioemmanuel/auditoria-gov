"use client";

import { useState, useMemo } from "react";
import { usePathname } from "next/navigation";
import {
  RadarBookContext,
  RadarBookRegistrationContext,
  buildRadarSequence,
  computeCurrentIndex,
} from "@/components/radar/RadarBookContext";
import RadarBookShell from "@/components/radar/RadarBookShell";
import type { BookPage, RadarBookContextValue, RadarBookRegistrationContextValue } from "@/lib/types";

export default function RadarLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [dossierPages, setDossierPages] = useState<BookPage[]>([]);

  // Extract activeCaseId from pathname: /radar/dossie/<caseId>/...
  const activeCaseId = useMemo<string | null>(() => {
    const match = /^\/radar\/dossie\/([^/]+)/.exec(pathname);
    return match?.[1] ?? null;
  }, [pathname]);

  // Build full page sequence
  const pages = useMemo<BookPage[]>(
    () => buildRadarSequence(pathname, activeCaseId, dossierPages),
    [pathname, activeCaseId, dossierPages],
  );

  const currentIndex = useMemo(
    () => computeCurrentIndex(pages, pathname),
    [pages, pathname],
  );

  const radarContextValue = useMemo<RadarBookContextValue>(
    () => ({ pages, currentIndex, activeCaseId }),
    [pages, currentIndex, activeCaseId],
  );

  const registrationContextValue = useMemo<RadarBookRegistrationContextValue>(
    () => ({ setDossierPages }),
    [setDossierPages],  // setDossierPages is stable (from useState)
  );

  return (
    <RadarBookContext.Provider value={radarContextValue}>
      <RadarBookRegistrationContext.Provider value={registrationContextValue}>
        <RadarBookShell>{children}</RadarBookShell>
      </RadarBookRegistrationContext.Provider>
    </RadarBookContext.Provider>
  );
}
