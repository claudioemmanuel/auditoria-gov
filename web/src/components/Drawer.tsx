"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  /** Max width class, default "max-w-2xl" */
  width?: string;
  /** Header action buttons */
  actions?: React.ReactNode;
}

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  className,
  width = "max-w-2xl",
  actions,
}: DrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 animate-[fadeIn_180ms_ease]"
        style={{ background: "rgba(8,14,26,0.6)", backdropFilter: "blur(1px)" }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          "fixed inset-y-0 right-0 z-50 flex w-full flex-col shadow-xl",
          "animate-[slideInRight_220ms_cubic-bezier(0.16,1,0.3,1)]",
          width,
          className,
        )}
        style={{
          background: "var(--color-surface-card)",
          borderLeft: "1px solid var(--border-light)",
        }}
      >
        {/* Header */}
        {(title || actions) && (
          <div
            className="flex items-start gap-3 px-5 py-4"
            style={{ borderBottom: "1px solid var(--border-light)" }}
          >
            <div className="flex-1">
              {title && (
                <h2
                  className="text-base font-semibold"
                  style={{ fontFamily: "var(--font-display)", color: "var(--color-text-primary)" }}
                >
                  {title}
                </h2>
              )}
              {subtitle && (
                <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  {subtitle}
                </p>
              )}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
            <button
              onClick={onClose}
              className="flex h-7 w-7 shrink-0 items-center justify-center transition-colors"
              style={{
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text-muted)",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLButtonElement).style.background = "var(--color-surface-hover)";
                (e.currentTarget as HTMLButtonElement).style.color = "var(--color-text-primary)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                (e.currentTarget as HTMLButtonElement).style.color = "var(--color-text-muted)";
              }}
              aria-label="Fechar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </div>
    </>
  );
}
