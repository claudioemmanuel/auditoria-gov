import Link from "next/link";
import { FileText, Github, Scale } from "lucide-react";

const REPOSITORY_URL = "https://github.com/claudioemmanuel/auditoria-gov";
const LICENSE_URL = "https://github.com/claudioemmanuel/auditoria-gov/blob/main/LICENSE";

export function SiteFooter() {
  return (
    <footer className="border-t border-gov-gray-200 bg-white px-4 py-7">
      <div className="mx-auto max-w-7xl space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <p className="text-sm font-semibold text-gov-gray-800">
            AuditorIA Gov is an open-source civic auditing project (AGPL-3.0).
          </p>

          <div className="flex flex-wrap items-center gap-4 text-sm">
            <Link
              href="/methodology"
              className="inline-flex items-center gap-1.5 text-gov-blue-700 hover:text-gov-blue-900"
            >
              <FileText className="h-4 w-4" />
              Metodologia
            </Link>
            <Link
              href={REPOSITORY_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-gov-blue-700 hover:text-gov-blue-900"
            >
              <Github className="h-4 w-4" />
              GitHub
            </Link>
            <Link
              href={LICENSE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-gov-blue-700 hover:text-gov-blue-900"
            >
              <Scale className="h-4 w-4" />
              Licenca AGPL-3.0
            </Link>
          </div>
        </div>

        <p className="text-sm text-gov-gray-600">
          Projeto de interesse publico para transparencia e controle social. Nao
          ha funcionalidade paga ou classificacao proprietaria de risco.
        </p>

        <p className="text-xs text-gov-gray-500">
          Os sinais apresentados sao indicadores estatisticos e nao constituem
          acusacao ou prova definitiva de irregularidade. Toda analise deve ser
          investigada com contraditorio e verificacao adicional.
        </p>
      </div>
    </footer>
  );
}
