"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";

interface Crumb {
  label: string;
  href?: string;
}

interface RadarBreadcrumbProps {
  crumbs: Crumb[];
  stickyTitle?: string;
  stickySeverity?: string;
  stickyValue?: string;
}

const SEV_DOT: Record<string, string> = {
  critical: "bg-error",
  high: "bg-amber",
  medium: "bg-yellow-500",
  low: "bg-info",
};

export function RadarBreadcrumb({ crumbs, stickyTitle, stickySeverity, stickyValue }: RadarBreadcrumbProps) {
  return (
    <div>
      <nav className="flex items-center gap-1.5 text-sm text-muted">
        {crumbs.map((c, i) => (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <ChevronRight className="h-3.5 w-3.5" />}
            {c.href ? (
              <Link
                href={c.href}
                className="hover:text-foreground transition-colors"
              >
                {c.label}
              </Link>
            ) : (
              <span className="text-foreground font-medium">{c.label}</span>
            )}
          </span>
        ))}
      </nav>
      {stickyTitle && (
        <div className="sticky top-0 z-10 -mx-4 mt-2 border-b border-border bg-surface/95 backdrop-blur px-4 py-2 sm:-mx-6 sm:px-6">
          <div className="flex items-center gap-2">
            {stickySeverity && (
              <span className={`h-2 w-2 rounded-full shrink-0 ${SEV_DOT[stickySeverity] ?? SEV_DOT.low}`} />
            )}
            <span className="text-sm font-medium text-primary truncate">{stickyTitle}</span>
            {stickyValue && (
              <span className="text-xs font-medium text-secondary ml-auto shrink-0">{stickyValue}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
