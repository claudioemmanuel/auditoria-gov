import { Suspense } from "react";
import ClientPage from "@/components/pages/EntityNetworkPage";

export function generateStaticParams() {
  return [{ entityId: "placeholder" }];
}

export default function Page(_: { params: Promise<Record<string, string>> }) {
  return <Suspense><ClientPage /></Suspense>;
}
