"use client";

import { useEffect, useRef, useCallback } from "react";
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

  // Escape to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px] animate-[fadeIn_180ms_ease]"
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
          "fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-border bg-surface-card shadow-xl",
          "animate-[slideInRight_220ms_cubic-bezier(0.16,1,0.3,1)]",
          width,
          className,
        )}
      >
        {/* Header */}
        {(title || actions) && (
          <div className="flex items-start gap-3 border-b border-border px-4 py-3">
            <div className="flex-1">
              {title && (
                <h2 className="font-display text-base font-semibold text-primary">
                  {title}
                </h2>
              )}
              {subtitle && (
                <p className="mt-0.5 text-xs text-secondary">{subtitle}</p>
              )}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
            <button
              onClick={onClose}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] text-muted transition-colors hover:bg-surface-subtle hover:text-primary"
              aria-label="Fechar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>

      {/* Animations */}
      <style jsx global>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideInRight {
          from {
            opacity: 0;
            transform: translateX(100%);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </>
  );
}
