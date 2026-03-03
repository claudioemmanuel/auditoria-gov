"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import {
  Activity,
  Radar,
  Database,
  BookOpen,
  Menu,
  X,
  Shield,
} from "lucide-react";

const ICON_MAP = {
  Activity,
  Radar,
  Database,
  BookOpen,
} as const;

export function Header() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-gradient-to-r from-gov-blue-900 to-gov-blue-800 text-white backdrop-blur">
      <div className="mx-auto flex max-w-[1280px] items-center justify-between px-4 py-3">
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/25 bg-white/10 text-white">
            <Shield className="h-5 w-5" />
          </span>
          <span className="leading-tight">
            <span className="block text-2xl font-extrabold tracking-tight sm:text-[1.65rem]">AuditorIA Gov</span>
            <span className="block text-[0.65rem] font-medium tracking-widest text-gov-blue-200 uppercase">Dados Públicos</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1.5 md:flex">
          {NAV_ITEMS.map((item) => {
            const Icon = ICON_MAP[item.icon];
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-[0.97rem] font-semibold tracking-tight transition",
                  isActive
                    ? "bg-white/15 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.12),inset_0_0_0_1px_rgba(255,255,255,0.2)]"
                    : "text-gov-blue-100 hover:bg-white/10 hover:text-white"
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
          className="rounded-lg border border-white/15 bg-white/5 p-2 text-gov-blue-100 hover:bg-white/10 md:hidden"
          aria-label="Menu"
        >
          {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile nav */}
      {menuOpen && (
        <nav className="border-t border-white/10 px-4 pb-3 md:hidden">
          {NAV_ITEMS.map((item) => {
            const Icon = ICON_MAP[item.icon];
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                className={cn(
                  "mt-1.5 flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-semibold transition",
                  isActive
                    ? "bg-white/15 text-white"
                    : "text-gov-blue-100 hover:bg-white/10"
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
