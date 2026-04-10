import { redirect } from "next/navigation";

/**
 * Signal domain index — redirects to Radar until the Signal feed is built.
 * The sidebar already renders Signal-specific nav for /signal/* routes.
 */
export default function SignalIndexPage() {
  redirect("/radar");
}
