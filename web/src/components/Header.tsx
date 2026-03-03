"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import {
  Radar,
  Database,
  BookOpen,
  Menu,
  X,
  Shield,
} from "lucide-react";

const ICON_MAP = {
  Radar,
  Database,
  BookOpen,
} as const;

export function Header() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="bg-gov-blue-800 text-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-xl font-bold tracking-tight">
          <Shield className="h-6 w-6" />
          AuditorIA Gov
        </Link>

        {/* Desktop nav */}
        <nav className="hidden gap-1 md:flex">
          {NAV_ITEMS.map((item) => {
            const Icon = ICON_MAP[item.icon];
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-gov-blue-900 text-white"
                    : "text-gov-blue-100 hover:bg-gov-blue-700"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Mobile menu button */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="rounded-md p-2 text-gov-blue-100 hover:bg-gov-blue-700 md:hidden"
          aria-label="Menu"
        >
          {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile nav */}
      {menuOpen && (
        <nav className="border-t border-gov-blue-700 px-4 pb-3 md:hidden">
          {NAV_ITEMS.map((item) => {
            const Icon = ICON_MAP[item.icon];
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-gov-blue-900 text-white"
                    : "text-gov-blue-100 hover:bg-gov-blue-700"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
