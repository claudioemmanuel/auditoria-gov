"use client";

import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";
import { cn } from "@/lib/utils";

interface ThemeToggleProps {
  collapsed?: boolean;
  className?: string;
}

export function ThemeToggle({ collapsed, className }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        "flex items-center gap-2 rounded-[10px] px-2.5 py-1.5 text-sm transition-colors",
        "text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active",
        className,
      )}
      aria-label={theme === "light" ? "Ativar modo escuro" : "Ativar modo claro"}
    >
      {theme === "light" ? (
        <Moon className="h-4 w-4 shrink-0" />
      ) : (
        <Sun className="h-4 w-4 shrink-0" />
      )}
      {!collapsed && (
        <span className="truncate">
          {theme === "light" ? "Modo escuro" : "Modo claro"}
        </span>
      )}
    </button>
  );
}
