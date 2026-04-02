"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface Option {
  value: string;
  label: string;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options?: Option[];
}

export function Select({ label, error, options, className, children, ...props }: SelectProps) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      {label && <label className="ow-label">{label}</label>}
      <select {...props} className={cn("ow-select w-full")}>
        {options ? options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        )) : children}
      </select>
      {error && <p className="text-xs text-[var(--color-destructive)] mt-1">{error}</p>}
    </div>
  );
}

export default Select;

