"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { RadarHeader } from "@/components/radar/RadarHeader";
import { FileText, Network, Scale } from "lucide-react";

const NAV_ITEMS = [
  { label: "Dossiês", href: "/radar", icon: FileText, match: (p: string) => p === "/radar" || p.startsWith("/radar/caso") },
  { label: "Rede", href: "/radar/rede", icon: Network, match: (p: string) => p.startsWith("/radar/rede") },
  { label: "Jurídico", href: "/radar/juridico", icon: Scale, match: (p: string) => p.startsWith("/radar/juridico") },
];

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

          {/* Navigation bar */}
          <nav className="mt-6 flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const active = item.match(pathname);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                    active
                      ? "bg-accent/10 text-accent border border-accent/20"
                      : "text-secondary hover:text-primary hover:bg-surface-subtle border border-transparent"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
      {children}
    </div>
  );
}
