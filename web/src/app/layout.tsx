import type { Metadata } from "next";
import { Manrope, Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppSidebar } from "@/components/AppSidebar";
import { ThemeProvider, ThemeScript } from "@/components/ThemeProvider";
import { CommandPalette } from "@/components/CommandPalette";
import { SiteFooter } from "@/components/SiteFooter";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "OpenWatch — Inteligencia Investigativa Cidada",
  description:
    "Plataforma publica e open-source de auditoria cidada sobre dados do governo federal brasileiro. Sinais de risco, evidencias e investigacoes baseadas em dados abertos.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body
        className={`${manrope.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} min-h-screen bg-surface-base`}
      >
        <ThemeProvider>
          <div className="flex h-screen overflow-hidden">
            <AppSidebar />
            <main className="flex-1 overflow-y-auto">
              {children}
              <SiteFooter />
            </main>
          </div>
          <CommandPalette />
        </ThemeProvider>
      </body>
    </html>
  );
}
