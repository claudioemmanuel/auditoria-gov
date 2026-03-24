"use client";

import { usePathname } from "next/navigation";
import { RadarHeader } from "@/components/radar/RadarHeader";

// Detail routes have their own dedicated page header — skip the section header
function isDetailRoute(pathname: string): boolean {
  return pathname.startsWith("/radar/dossie/") || /^\/radar\/rede\/[^/]+/.test(pathname);
}

export default function RadarLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  if (isDetailRoute(pathname)) {
    return <div className="flex min-h-screen flex-col">{children}</div>;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <div className="border-b border-border bg-surface-card">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          <RadarHeader />
        </div>
      </div>
      {children}
    </div>
  );
}
