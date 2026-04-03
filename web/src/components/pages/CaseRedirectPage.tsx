"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";


export default function CaseRedirectPage() {
  const params = useParams<{ caseId: string }>();
  const router = useRouter();

  useEffect(() => {
    if (params.caseId) {
      router.replace(`/radar/dossie/${params.caseId}`);
    }
  }, [params.caseId, router]);

  return null;
}
