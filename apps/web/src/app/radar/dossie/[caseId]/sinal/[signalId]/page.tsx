import { Suspense } from "react";
import ClientPage from "@/components/pages/SinalPage";

export function generateStaticParams() {
  return [{ caseId: "placeholder", signalId: "placeholder" }];
}

export default function Page(_: { params: Promise<Record<string, string>> }) {
  return <Suspense><ClientPage /></Suspense>;
}
