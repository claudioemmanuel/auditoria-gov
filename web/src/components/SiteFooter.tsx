import Link from "next/link";

const REPOSITORY_URL = "https://github.com/claudioemmanuel/auditoria-gov";
const LICENSE_URL = "https://github.com/claudioemmanuel/auditoria-gov/blob/main/LICENSE";

export function SiteFooter() {
  return (
    <footer className="border-t border-border px-6 py-3">
      <p className="text-xs text-muted">
        &copy; 2025 AuditorIA Gov &middot;{" "}
        <Link href="/methodology" className="hover:text-accent">
          Metodologia
        </Link>{" "}
        &middot;{" "}
        <Link
          href={REPOSITORY_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-accent"
        >
          GitHub
        </Link>{" "}
        &middot;{" "}
        <Link
          href={LICENSE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-accent"
        >
          AGPL-3.0
        </Link>{" "}
        &middot; Dados publicos &middot; Sem fins lucrativos
      </p>
    </footer>
  );
}
