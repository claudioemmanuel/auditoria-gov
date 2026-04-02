"use client";

import { clsx } from "clsx";
import type { ReactNode } from "react";

/* ── Tabs Container ─────────────────────────────────────────────── */
interface TabsProps {
  children: ReactNode;
  className?: string;
}

export function Tabs({ children, className }: TabsProps) {
  return (
    <div className={clsx("ow-tabs overflow-x-auto", className)} role="tablist">
      {children}
    </div>
  );
}

/* ── Tab Item ───────────────────────────────────────────────────── */
interface TabProps {
  active?: boolean;
  onClick?: () => void;
  children: ReactNode;
  count?: number;
  className?: string;
  href?: string;
}

export function Tab({ active, onClick, children, count, className, href }: TabProps) {
  const classes = clsx("ow-tab", active && "active", className);

  if (href) {
    return (
      <a href={href} className={classes} aria-selected={active} role="tab">
        {children}
        {count !== undefined && <span className="ow-tab-count">{count}</span>}
      </a>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={classes}
      aria-selected={active}
      role="tab"
    >
      {children}
      {count !== undefined && <span className="ow-tab-count">{count}</span>}
    </button>
  );
}
