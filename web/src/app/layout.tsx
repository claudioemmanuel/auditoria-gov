import type { Metadata } from "next";
import { Inter, IBM_Plex_Mono, DM_Sans } from "next/font/google";
import "./globals.css";
import { AppSidebar } from "@/components/AppSidebar";
import { ThemeProvider, ThemeScript } from "@/components/ThemeProvider";
import { CommandPalette } from "@/components/CommandPalette";
import { SiteFooter } from "@/components/SiteFooter";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-mono",
});
const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-display",
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
        className={`${inter.variable} ${ibmPlexMono.variable} ${dmSans.variable} antialiased`}
        style={{ paddingTop: "40px" }}
      >
        <ThemeProvider>
          <div className="relative z-50">
            <CommandPalette />
          </div>
          <AppSidebar />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
