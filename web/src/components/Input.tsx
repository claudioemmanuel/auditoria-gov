import { clsx } from "clsx";
import type { InputHTMLAttributes, SelectHTMLAttributes, LabelHTMLAttributes, TextareaHTMLAttributes } from "react";

/* ── Input ──────────────────────────────────────────────────────── */
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  iconLeft?: React.ReactNode;
  error?: string;
}

export function Input({ label, iconLeft, error, className, ...props }: InputProps) {
  return (
    <div className="relative w-full flex flex-col gap-1">
      {label && <label className="ow-label">{label}</label>}
      <div className="relative">
        {iconLeft && (
          <span
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-3)]"
            style={{ width: 14, height: 14 }}
          >
            {iconLeft}
          </span>
        )}
        <input
          className={clsx(
            "ow-input",
            iconLeft && "ow-input-icon-left",
            error && "!border-[var(--color-critical)]",
            className
          )}
          {...props}
        />
      </div>
      {error && (
        <p className="mt-1 text-xs text-[var(--color-critical-text)]">{error}</p>
      )}
    </div>
  );
}

/* ── Select ─────────────────────────────────────────────────────── */
export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={clsx("ow-select", className)} {...props} />;
}

/* ── Label ──────────────────────────────────────────────────────── */
export function Label({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={clsx("ow-label", className)} {...props} />;
}

/* ── Textarea ───────────────────────────────────────────────────── */
export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={clsx("ow-input resize-none", className)}
      {...props}
    />
  );
}

/* ── Field (label + input wrapper) ─────────────────────────────── */
interface FieldProps {
  label?: string;
  htmlFor?: string;
  error?: string;
  children: React.ReactNode;
  className?: string;
}

export function Field({ label, htmlFor, error, children, className }: FieldProps) {
  return (
    <div className={clsx("ow-field", className)}>
      {label && <label htmlFor={htmlFor} className="ow-label">{label}</label>}
      {children}
      {error && <p className="text-xs text-[var(--color-critical-text)]">{error}</p>}
    </div>
  );
}
