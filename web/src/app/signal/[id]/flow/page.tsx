"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function SignalFlowPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  useEffect(() => {
    if (params.id) {
      router.replace(`/signal/${params.id}/graph`);
    }
  }, [params.id, router]);

  return null;
}
