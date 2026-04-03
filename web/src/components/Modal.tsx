"use client";

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children?: React.ReactNode;
  className?: string;
  closeLabel?: string;
}

export function Modal({ open, onClose, title, children, className, closeLabel = "Close" }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const titleId = title ? "modal-title" : undefined;

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
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div ref={overlayRef} className="absolute inset-0 bg-black/45" onClick={onClose} />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cn(
          "relative bg-[var(--color-surface-card)] border border-[var(--color-border-light)] rounded-lg p-6 w-full max-w-2xl shadow-[var(--shadow-xl)]",
          className,
        )}
      >
        <div className="flex items-start justify-between gap-4">
          {title && (
            <h3 id={titleId} className="text-lg font-semibold text-[var(--color-text-primary)]">
              {title}
            </h3>
          )}

          <button
            aria-label={closeLabel}
            onClick={onClose}
            className="ml-auto text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}

export default Modal;
