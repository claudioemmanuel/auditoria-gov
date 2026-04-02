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
          "inline-flex cursor-pointer items-center gap-2 text-sm",
          props.disabled && "cursor-not-allowed opacity-50",
          className,
        )}
        style={{ color: "var(--color-text-secondary)" }}
      >
        <input
          ref={ref}
          id={checkboxId}
          type="checkbox"
          className="shrink-0 cursor-pointer"
          style={{
            width: "16px",
            height: "16px",
            borderRadius: "var(--radius-xs)",
            accentColor: "var(--color-accent-trust)",
            outline: "none",
          }}
          onFocus={e => {
            (e.currentTarget as HTMLInputElement).style.boxShadow = "var(--shadow-focus)";
          }}
          onBlur={e => {
            (e.currentTarget as HTMLInputElement).style.boxShadow = "";
          }}
          {...props}
        />
        {label && <span>{label}</span>}
      </label>
    );
  },
);
Checkbox.displayName = "Checkbox";
