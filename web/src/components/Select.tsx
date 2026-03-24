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
          <label htmlFor={selectId} className="text-xs font-medium text-secondary">
            {label}
          </label>
        )}
        <div
          className={cn(
            "relative flex items-center gap-2 bg-surface-card px-3 py-2 transition-colors duration-120",
            "focus-within:outline-none",
            props.disabled && "opacity-50",
            className,
          )}
          style={{
            border: error ? "1px solid var(--color-error)" : "1px solid var(--color-border)",
            borderRadius: 0,
            ...style,
          }}
        >
          {Icon && <Icon className="h-4 w-4 shrink-0 text-muted" />}
          <select
            ref={ref}
            id={selectId}
            className="w-full appearance-none border-none bg-transparent pr-6 text-sm text-primary outline-none disabled:cursor-not-allowed focus:outline-none"
            style={{ borderRadius: 0 }}
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
          <ChevronDown className="pointer-events-none absolute right-3 h-4 w-4 text-muted" />
        </div>
        {error && <p className="text-xs text-error">{error}</p>}
      </div>
    );
  },
);
Select.displayName = "Select";
