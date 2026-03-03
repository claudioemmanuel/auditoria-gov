"use client";

import { Radar } from "lucide-react";
import { PageHero } from "@/components/PageHero";

export function RadarHeader() {
  return (
    <PageHero
      icon={Radar}
      title="Central de Riscos"
      description="Triagem investigativa dos sinais e casos consolidados, com foco em contexto, gravidade e explicabilidade para apoiar a priorização da análise."
      note="os resultados indicam prioridade técnica de análise. Não representam acusação, prova definitiva ou conclusão judicial."
    />
  );
}
