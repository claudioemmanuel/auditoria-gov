import { forwardRef } from "react";
import type { LucideIcon } from "lucide-react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  icon?: LucideIcon;
  error?: string;
  options: { value: string; label: string }[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, icon: Icon, error, options, placeholder, id, style, ...props }, ref) => {
    const selectId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={selectId} className="text-xs font-medium" style={{ color: "var(--color-text-primary)" }}>
            {label}
          </label>
        )}
        <div
          className={cn(
            "relative flex items-center gap-2 px-3 py-2 bg-white transition-all duration-150",
            "focus-within:outline-none",
            props.disabled && "opacity-50",
            className,
          )}
          style={{
            border: error
              ? "1px solid var(--color-error)"
              : "1px solid var(--border-light)",
            borderRadius: "var(--radius-sm)",
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
          <select
            ref={ref}
            id={selectId}
            className="w-full appearance-none border-none bg-transparent pr-6 text-sm outline-none disabled:cursor-not-allowed focus:outline-none"
            style={{
              color: "var(--color-text-primary)",
              borderRadius: "var(--radius-sm)",
            }}
            {...props}
          >
            {placeholder && (
              <option value="">{placeholder}</option>
            )}
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown
            className="pointer-events-none absolute right-3 h-4 w-4"
            style={{ color: "var(--color-text-muted)" }}
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
Select.displayName = "Select";
