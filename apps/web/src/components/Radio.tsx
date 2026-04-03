"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface RadioProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const Radio = React.forwardRef<HTMLInputElement, RadioProps>(({ label, className, ...props }, ref) => {
  return (
    <label className={cn("inline-flex items-center gap-2 cursor-pointer", className)}>
      <input
        ref={ref}
        type="radio"
        className="h-4 w-4 rounded-full border-[var(--color-border-light)] text-[var(--color-accent-alert)]"
        {...props}
      />
      {label && <span className="text-sm text-[var(--color-text-primary)]">{label}</span>}
    </label>
  );
});
Radio.displayName = "Radio";

export default Radio;
