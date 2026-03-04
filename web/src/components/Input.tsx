import { forwardRef } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  icon?: LucideIcon;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, icon: Icon, error, id, ...props }, ref) => {
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
            "flex items-center gap-2 rounded-[10px] border bg-surface-card px-3 py-2 transition-colors duration-120",
            "focus-within:border-accent focus-within:ring-1 focus-within:ring-accent/20",
            error ? "border-error" : "border-border",
            props.disabled && "opacity-50",
            className,
          )}
        >
          {Icon && <Icon className="h-4 w-4 shrink-0 text-muted" />}
          <input
            ref={ref}
            id={inputId}
            className="w-full border-none bg-transparent text-sm text-primary outline-none placeholder:text-placeholder disabled:cursor-not-allowed"
            {...props}
          />
        </div>
        {error && <p className="text-xs text-error">{error}</p>}
      </div>
    );
  },
);
Input.displayName = "Input";
