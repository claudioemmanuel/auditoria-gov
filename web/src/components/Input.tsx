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
          <label htmlFor={inputId} className="text-xs font-medium text-secondary">
            {label}
          </label>
        )}
        <div
          className={cn(
            "flex items-center gap-2 bg-transparent px-2 py-1.5 transition-colors duration-100",
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
          <input
            ref={ref}
            id={inputId}
            className="w-full border-none bg-transparent text-sm text-primary outline-none placeholder:text-placeholder disabled:cursor-not-allowed focus:outline-none"
            style={{ borderRadius: 0 }}
            {...props}
          />
        </div>
        {error && <p className="text-xs text-error">{error}</p>}
      </div>
    );
  },
);
Input.displayName = "Input";
