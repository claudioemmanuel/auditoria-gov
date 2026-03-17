import { permanentRedirect } from "next/navigation";

export default async function SignalRedirectPage({
  params,
}: {
  params: Promise<{ caseId: string; signalId: string }>;
}) {
  const { caseId, signalId } = await params;
  permanentRedirect(`/radar/dossie/${caseId}/sinal/${signalId}`);
}
