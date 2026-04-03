"use client";

import React, { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children?: React.ReactNode;
  width?: string;
  className?: string;
  side?: "right" | "left";
}

export function Drawer({ open, onClose, title, children, width = "w-96", className, side = "right" }: DrawerProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside
        className={cn(
          "relative h-full bg-[var(--color-surface-card)] border-l border-[var(--color-border-light)] p-4 shadow-[var(--shadow-xl)] overflow-auto",
          className,
          side === "right" ? "ml-auto" : "mr-auto",
          width,
        )}
      >
        <div className="flex items-center justify-between mb-4">
          {title && <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">{title}</h3>}
          <button aria-label="Close" onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div>{children}</div>
      </aside>
    </div>
  );
}

export default Drawer;
 
