"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(({ label, className, ...props }, ref) => {
  return (
    <label className={cn("inline-flex items-center gap-2 cursor-pointer", className)}>
      <input
        ref={ref}
        type="checkbox"
        className="h-4 w-4 rounded border-[var(--color-border-light)] text-[var(--color-accent-alert)]"
        {...props}
      />
      {label && <span className="text-sm text-[var(--color-text-primary)]">{label}</span>}
    </label>
  );
});
Checkbox.displayName = "Checkbox";

export default Checkbox;

