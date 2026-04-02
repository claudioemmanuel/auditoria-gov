import type { Metadata } from "next";
import { DM_Sans, Syne, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppSidebar } from "@/components/AppSidebar";
import { Header } from "@/components/Header";
import { SiteFooter } from "@/components/SiteFooter";
import { CommandPalette } from "@/components/CommandPalette";

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const syne = Syne({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-display",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
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
        className={`${dmSans.variable} ${syne.variable} ${jetbrainsMono.variable}`}
      >
        {/* Skip-to-content — WCAG 2.4.1 */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[9999] focus:inline-flex focus:items-center focus:gap-2 focus:rounded focus:bg-[var(--color-amber)] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-[var(--color-text-inv)] focus:outline-none"
        >
          Ir para o conteúdo principal
        </a>

        <CommandPalette />

        {/* Mobile header — visible below md breakpoint */}
        <Header />

        <div className="ow-page" style={{ paddingTop: "var(--header-height)" }}>
          {/* Desktop sidebar — hidden on mobile */}
          <div className="hidden md:flex md:flex-shrink-0" style={{ marginTop: "calc(-1 * var(--header-height))" }}>
            <AppSidebar />
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
