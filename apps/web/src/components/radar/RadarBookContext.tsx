"use client";

import { createContext, useContext } from "react";
import type {
  BookPage,
  RadarBookContextValue,
  RadarBookRegistrationContextValue,
} from "@/lib/types";

export const RadarBookContext = createContext<RadarBookContextValue>({
  pages: [],
  currentIndex: -1,
  activeCaseId: null,
});

export function useRadarBook(): RadarBookContextValue {
  return useContext(RadarBookContext);
}

export const RadarBookRegistrationContext =
  createContext<RadarBookRegistrationContextValue>({
    setDossierPages: () => {},
  });

export function useRadarBookRegistration(): RadarBookRegistrationContextValue {
  return useContext(RadarBookRegistrationContext);
}

const STATIC_RADAR_PAGES: BookPage[] = [
  { type: "radar-hub", href: "/radar", label: "Visão Geral" },
  { type: "radar-rede", href: "/radar/rede", label: "Rede de Entidades" },
  { type: "radar-juridico", href: "/radar/juridico", label: "Base Jurídica" },
];

export function buildRadarSequence(
  _pathname: string,
  activeCaseId: string | null,
  dossierPages: BookPage[],
): BookPage[] {
  const pages: BookPage[] = [...STATIC_RADAR_PAGES];

  if (activeCaseId !== null && dossierPages.length > 0) {
    pages.push(...dossierPages);
  }

  return pages;
}

export function computeCurrentIndex(
  pages: BookPage[],
  pathname: string,
): number {
  const exact = pages.findIndex((p) => p.href === pathname);
  if (exact !== -1) return exact;

  const stripped = pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
  return pages.findIndex((p) => p.href === stripped);
}
