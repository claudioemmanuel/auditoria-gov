import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface PageHeroProps {
  icon: LucideIcon;
  title: string;
  description: string;
  note: string;
  noteTitle?: string;
  aside?: ReactNode;
}

export function PageHero(_props: PageHeroProps) {
  return null;
}
