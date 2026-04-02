import { forwardRef } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  icon?: LucideIcon;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, icon: Icon, error, id, style, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={inputId} className="text-xs font-medium" style={{ color: "var(--color-text-primary)" }}>
            {label}
          </label>
        )}
        <div
          className={cn(
            "flex items-center gap-2 px-3 py-2 bg-white transition-all duration-150",
            "focus-within:outline-none",
            props.disabled && "opacity-50",
            className,
          )}
          style={{
            border: error
              ? "1px solid var(--color-error)"
              : "1px solid var(--border-light)",
            borderRadius: "var(--radius-sm)",
            // @ts-expect-error – CSS variable assignment for focus ring via parent focus-within
            "--focus-shadow": "var(--shadow-focus)",
            ...style,
          }}
          onFocusCapture={e => {
            (e.currentTarget as HTMLDivElement).style.boxShadow = "var(--shadow-focus)";
            (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-focus)";
          }}
          onBlurCapture={e => {
            (e.currentTarget as HTMLDivElement).style.boxShadow = "";
            (e.currentTarget as HTMLDivElement).style.borderColor = error
              ? "var(--color-error)"
              : "var(--border-light)";
          }}
        >
          {Icon && <Icon className="h-4 w-4 shrink-0" style={{ color: "var(--color-text-muted)" }} />}
          <input
            ref={ref}
            id={inputId}
            className="w-full border-none bg-transparent text-sm outline-none placeholder:opacity-50 disabled:cursor-not-allowed focus:outline-none"
            style={{
              color: "var(--color-text-primary)",
              borderRadius: "var(--radius-sm)",
            }}
            {...props}
          />
        </div>
        {error && (
          <p className="text-xs" style={{ color: "var(--color-error)" }}>
            {error}
          </p>
        )}
      </div>
    );
  },
);
Input.displayName = "Input";
