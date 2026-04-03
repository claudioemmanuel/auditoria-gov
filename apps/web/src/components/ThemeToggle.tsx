"use client";

import { Moon } from "lucide-react";
import { cn } from "@/lib/utils";

interface ThemeToggleProps {
  collapsed?: boolean;
  className?: string;
}

export function ThemeToggle({ collapsed, className }: ThemeToggleProps) {
  return (
    <button
      disabled
      className={cn(
        "flex items-center gap-2 rounded-[10px] px-2.5 py-1.5 text-sm opacity-40 cursor-not-allowed",
        "text-sidebar-text",
        className,
      )}
      aria-label="Modo escuro (padrão)"
    >
      <Moon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">Modo escuro</span>}
    </button>
  );
}
