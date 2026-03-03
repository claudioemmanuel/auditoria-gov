import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "AuditorIA Gov — Auditoria Cidada",
  description:
    "Portal publico para auditoria cidada de dados do governo federal brasileiro",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="flex min-h-screen flex-col">
        <Header />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-gov-gray-200 bg-white px-4 py-6">
          <div className="mx-auto max-w-7xl text-center text-sm text-gov-gray-500">
            <p className="font-medium text-gov-gray-700">
              AuditorIA Gov — Ferramenta de auditoria cidada baseada em dados
              publicos
            </p>
            <p className="mt-1">
              Os sinais apresentados sao indicadores estatisticos e nao
              constituem acusacao ou prova de irregularidade.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
