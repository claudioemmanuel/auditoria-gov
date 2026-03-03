"use client";

import { Radar } from "lucide-react";

export function RadarHeader() {
  return (
    <div className="mt-4 flex items-center gap-3">
      <div className="rounded-xl bg-gov-blue-50 p-2.5">
        <Radar className="h-6 w-6 text-gov-blue-600" />
      </div>
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gov-gray-900">
          Central de Riscos
        </h1>
        <p className="text-sm text-gov-gray-500">
          Triagem investigativa com visoes por sinais e por casos consolidados.
        </p>
      </div>
    </div>
  );
}
