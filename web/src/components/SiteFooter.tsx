import Link from "next/link";

const REPOSITORY_URL = "https://github.com/claudioemmanuel/auditoria-gov";
const LICENSE_URL = "https://github.com/claudioemmanuel/auditoria-gov/blob/main/LICENSE";

export function SiteFooter() {
  return (
    <footer className="border-t border-gov-gray-200 bg-white px-6 py-3">
      <p className="text-xs text-gov-gray-500">
        &copy; 2025 AuditorIA Gov &middot;{" "}
        <Link href="/methodology" className="hover:text-gov-blue-700">
          Metodologia
        </Link>{" "}
        &middot;{" "}
        <Link
          href={REPOSITORY_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-gov-blue-700"
        >
          GitHub
        </Link>{" "}
        &middot;{" "}
        <Link
          href={LICENSE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-gov-blue-700"
        >
          AGPL-3.0
        </Link>{" "}
        &middot; Dados públicos &middot; Sem fins lucrativos
      </p>
    </footer>
  );
}
