import { Suspense } from "react";
import ClientPage from "@/components/pages/CapituloPage";

export function generateStaticParams() {
  return [{ caseId: "placeholder", typologyCode: "placeholder" }];
}

export default function Page(_: { params: Promise<Record<string, string>> }) {
  return <Suspense><ClientPage /></Suspense>;
}
