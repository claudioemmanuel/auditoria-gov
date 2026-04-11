"use client";

import { useState } from "react";
import { RadarBookTOC } from "./RadarBookTOC";
import { BookNav } from "./BookNav";

interface RadarBookShellProps {
  children: React.ReactNode;
}

export default function RadarBookShell({ children }: RadarBookShellProps): React.JSX.Element {
  const [tocOpen, setTocOpen] = useState(false);

  return (
    <>
      <div className="flex min-h-screen">
        <RadarBookTOC mobileOpen={tocOpen} onMobileClose={() => setTocOpen(false)} />
        <main className="flex-1 min-w-0 pb-14">
          {children}
        </main>
      </div>

      <BookNav onOpenTOC={() => setTocOpen(true)} />
    </>
  );
}
