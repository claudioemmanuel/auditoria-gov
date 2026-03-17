import { permanentRedirect } from "next/navigation";

export default async function CaseRedirectPage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  permanentRedirect(`/radar/dossie/${caseId}`);
}
