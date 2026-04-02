"use client";

import { usePathname } from "next/navigation";

export default function RadarLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      {children}
    </div>
  );
}
