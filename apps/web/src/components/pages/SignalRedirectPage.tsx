"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";


export default function SignalRedirectPage() {
  const params = useParams<{ caseId: string; signalId: string }>();
  const router = useRouter();

  useEffect(() => {
    if (params.caseId && params.signalId) {
      router.replace(`/radar/dossie/${params.caseId}/sinal/${params.signalId}`);
    }
  }, [params.caseId, params.signalId, router]);

  return null;
}
