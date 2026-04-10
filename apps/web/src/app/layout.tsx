import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist, Geist_Mono, Inter } from "next/font/google";
import "./globals.css";
import { AppSidebar } from "@/components/AppSidebar";
import { Topbar } from "@/components/Topbar";
import { SiteFooter } from "@/components/SiteFooter";
import { CommandPalette } from "@/components/CommandPalette";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    template: "%s — OpenWatch",
    default: "OpenWatch — Inteligência Investigativa Cidadã",
  },
  description:
    "Plataforma pública e open-source de auditoria cidadã sobre dados do governo federal brasileiro. Sinais de risco, evidências e investigações baseadas em dados abertos.",
  keywords: [
    "auditoria cidadã", "corrupção", "licitação", "governo federal",
    "dados abertos", "transparência", "Brasil", "PNCP", "ComprasGov",
  ],
  openGraph: {
    title: "OpenWatch — Inteligência Investigativa Cidadã",
    description: "Plataforma de auditoria cidadã sobre dados do governo federal brasileiro.",
    type: "website",
    locale: "pt_BR",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="pt-BR"
      className="dark"
      suppressHydrationWarning
    >
      <head>
        <meta name="color-scheme" content="dark" />
      </head>
      <body
        className={`${inter.variable} ${geist.variable} ${geistMono.variable}`}
      >
        {/* Skip-to-content — WCAG 2.4.1 */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[9999] focus:inline-flex focus:items-center focus:gap-2 focus:rounded focus:bg-[var(--color-amber)] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-[var(--color-text-inv)] focus:outline-none"
        >
          Ir para o conteúdo principal
        </a>

        <CommandPalette />

        {/* Global topbar — all viewports */}
        <Topbar />

        <div className="ow-page" style={{ paddingTop: "var(--topbar-height)" }}>
          {/* Sidebar — hidden on mobile */}
          <div className="hidden md:flex md:flex-shrink-0">
            <Suspense fallback={<div style={{ width: "var(--sidebar-width)" }} aria-hidden="true" />}>
              <AppSidebar />
            </Suspense>
          </div>

          <main id="main-content" className="ow-main" tabIndex={-1}>
            {children}
            <SiteFooter />
          </main>
        </div>
      </body>
    </html>
  );
}
