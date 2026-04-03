"use client";

import { Radar } from "lucide-react";

export function RadarHeader() {
  return (
    <div className="flex items-start gap-4">
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent-subtle border border-accent/20">
        <Radar className="h-6 w-6 text-accent" />
      </div>
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-primary sm:text-3xl">Investigacao</h1>
        <p className="mt-1.5 text-sm text-secondary leading-relaxed">Central de investigacao, sinais e inteligencia em dados publicos federais</p>
      </div>
    </div>
  );
}
