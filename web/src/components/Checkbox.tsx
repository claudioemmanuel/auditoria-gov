import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, ...props }, ref) => {
    const checkboxId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <label
        htmlFor={checkboxId}
        className={cn(
          "inline-flex cursor-pointer items-center gap-2 text-sm text-secondary",
          props.disabled && "cursor-not-allowed opacity-50",
          className,
        )}
      >
        <input
          ref={ref}
          id={checkboxId}
          type="checkbox"
          className="h-4 w-4 rounded border-border text-accent accent-accent focus:ring-accent"
          {...props}
        />
        {label && <span>{label}</span>}
      </label>
    );
  },
);
Checkbox.displayName = "Checkbox";
