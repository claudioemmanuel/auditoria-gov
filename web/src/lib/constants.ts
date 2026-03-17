export const SEVERITY_LABELS: Record<string, string> = {
  low: "Baixo",
  medium: "Médio",
  high: "Alto",
  critical: "Crítico",
};

export const TYPOLOGY_LABELS: Record<string, string> = {
  T01: "Concentração em Fornecedor",
  T02: "Baixa Competição",
  T03: "Fracionamento de Despesa",
  T04: "Aditivo Outlier",
  T05: "Preço Outlier",
  T06: "Proxy de Empresa de Fachada",
  T07: "Rede de Cartel",
  T08: "Sanção x Contrato",
  T09: "Proxy de Folha Fantasma",
  T10: "Terceirização Paralela",
  T11: "Jogo de Planilha",
  T12: "Edital Direcionado",
  T13: "Conflito de Interesses",
  T14: "Sequência de Favorecimento Contratual",
  T15: "Inexigibilidade Indevida",
  T16: "Clientelismo Orçamentário-Contratual",
  T17: "Lavagem via Camadas Societárias",
  T18: "Acúmulo Ilegal de Cargos",
  T19: "Rotação de Vencedores",
  T20: "Licitantes Fantasmas",
  T21: "Cluster Colusivo",
  T22: "Favorecimento Político",
};

export const TYPOLOGY_INFO: Record<string, { description: string; legal: string }> = {
  T01: {
    description:
      "Detecta quando um único fornecedor concentra mais de 70% do valor contratado por um órgão em determinada categoria de produto/serviço (HHI > 0,70). Alta concentração sugere direcionamento de contratos ou cartelização.",
    legal: "Lei 8.666/93, Art. 3° | Lei 14.133/2021, Art. 9° | Lei 12.529/2011 (CADE)",
  },
  T02: {
    description:
      "Identifica licitações com número de participantes abaixo do percentil 10 do histórico de licitações similares. Pouca competição pode indicar edital restritivo, combinação prévia entre empresas ou afastamento de concorrentes.",
    legal: "Lei 8.666/93, Art. 3°, §1° | Lei 14.133/2021, Art. 9° | Lei 8.429/92, Art. 10",
  },
  T03: {
    description:
      "Detecta compras repetidas do mesmo item em janela de 30 dias cujo valor somado ultrapassa os limites legais de dispensa de licitação. Fracionamento artificial é prática vedada para contornar exigência de certame.",
    legal: "Lei 8.666/93, Art. 24, I e II | Lei 14.133/2021, Art. 75, I e II | TCU Súmula 249",
  },
  T04: {
    description:
      "Sinaliza aditivos contratuais cujo valor supera 25% do contrato original (limite legal para obras e serviços). Aditivos excessivos podem indicar superfaturamento planejado ou escopo subdeclarado no contrato original.",
    legal: "Lei 8.666/93, Art. 65, §1° | Lei 14.133/2021, Art. 125 | TCU Acórdão 2618/2020",
  },
  T05: {
    description:
      "Compara o preço unitário de itens licitados com a mediana de contratos similares (mesmo CATMAT). Preços acima de 1,5× a mediana indicam possível superfaturamento em relação ao mercado.",
    legal: "Lei 8.666/93, Art. 15, V | IN SEGES 73/2022 | TCU Acórdão 1977/2013",
  },
  T06: {
    description:
      "Identifica empresas vencedoras com sinais de empresa de fachada: CNPJ recente (<180 dias), capital social abaixo de R$ 10 mil, sem funcionários registrados ou endereço suspeito. Empresas de fachada são usadas para desvio de recursos públicos.",
    legal: "Lei 8.429/92, Art. 10 | Lei 12.846/2013, Art. 5° | FATF Recomendação 24",
  },
  T07: {
    description:
      "Detecta redes de empresas com mesmos sócios, endereços compartilhados ou padrões de lance coordenados que sugerem formação de cartel em licitações. Conluio entre concorrentes viola a livre competição.",
    legal: "Lei 12.529/2011, Art. 36, III | Lei 14.133/2021, Art. 155, IV | CP Art. 335-A",
  },
  T08: {
    description:
      "Cruza empresas vencedoras de contratos com registros de sanções administrativas ativas (CEIS, CNEP, CEPIM). Contratar empresa punida é vedado por lei e indica falha de controle interno ou desvio intencional.",
    legal: "Lei 8.429/92 | Lei 12.846/2013, Art. 19 | Decreto 11.129/2022 (CEIS/CNEP)",
  },
  T09: {
    description:
      "Identifica servidores com remuneração que excede em mais de 2 desvios-padrão a mediana do cargo, ou servidores com CPF duplicado. Pode indicar pagamentos a servidores fantasmas ou erros de cadastro na folha.",
    legal: "Lei 8.112/1990 | Lei 8.429/92, Art. 9° | TCU Acórdão 1947/2017",
  },
  T10: {
    description:
      "Detecta contratos de terceirização onde os trabalhadores prestam serviços típicos do órgão contratante, podendo caracterizar vínculo empregatício disfarçado ou desvio da vedação constitucional ao provimento irregular.",
    legal: "CF/88, Art. 37, II | Súmula 331/TST | Lei 13.429/2017 | Lei 14.133/2021",
  },
  T11: {
    description:
      "Identifica padrões suspeitos em planilhas de composição de preços: itens com arredondamento excessivo, coeficientes idênticos entre propostas concorrentes ou valores que batem exatamente com estimativas sigilosas.",
    legal: "Lei 8.666/93, Art. 44, §2° | IN SEGES 65/2021 | TCU Acórdão 1977/2013",
  },
  T12: {
    description:
      "Detecta editais de licitação com especificações técnicas altamente restritivas, exigências desnecessárias ou prazos de resposta anormalmente curtos, favorecendo um fornecedor específico em detrimento da ampla concorrência.",
    legal: "Lei 8.666/93, Art. 3°, §1°, I | Lei 14.133/2021, Art. 9° | TCU Súmula 177",
  },
  T13: {
    description:
      "Cruza servidores públicos envolvidos em decisões de compras com dados de sócios de empresas fornecedoras, identificando possíveis conflitos de interesse entre agentes públicos e beneficiários privados.",
    legal: "Lei 12.813/2013 (Conflito de Interesses) | Lei 8.429/92, Art. 9° | CF/88, Art. 37, §4°",
  },
  T14: {
    description:
      "Tipologia composta: agrega sinais de T01, T02, T04, T05, T06, T07, T11 e T12 referentes à mesma entidade ao longo do tempo. Quando 2+ tipologias distintas se acumulam (meta-score ≥ 4) por mais de 180 dias, indica favorecimento contratual sistemático.",
    legal: "CP Arts. 317/333 | Lei 12.846/2013, Art. 5° | Lei 8.429/92, Art. 10",
  },
  T15: {
    description:
      "Identifica contratos firmados por inexigibilidade de licitação (fornecedor exclusivo) em categorias onde existem 3+ fornecedores competindo em certames similares. Indica uso indevido da dispensa para beneficiar fornecedor preferido.",
    legal: "Lei 14.133/2021, Art. 74 | Lei 8.666/93, Art. 25 | Lei 8.429/92, Art. 10, VII",
  },
  T16: {
    description:
      "Detecta emendas parlamentares e transferências especiais sem plano de trabalho registrado, com valor desproporcional à receita municipal ou direcionadas sistematicamente para os mesmos municípios por um único relator (HHI > 0,70).",
    legal: "CF/88, Art. 166-A | TCU Acórdão 518/2023 | STF Min. Flávio Dino 2024 | Decreto 11.878/2024",
  },
  T17: {
    description:
      "Detecta fornecedores vencedores de contratos que formam ciclos societários de até 3 saltos (A→B→C→A), indicando estrutura de camadas para dissimular o beneficiário final (UBO) e possível lavagem de dinheiro via contratos públicos.",
    legal: "Lei 9.613/1998, Art. 1° | FATF Recomendação 24 | FATF Recomendação 3",
  },
  T18: {
    description:
      "Identifica servidores com vínculos simultâneos em 2+ órgãos por mais de 90 dias, o que é vedado pela Constituição exceto em casos específicos. Cruza com o CEAF (Cadastro de Expulsados) para agravamento da severidade.",
    legal: "CF/88, Arts. 37, XVI-XVII | Lei 8.112/1990, Arts. 118-120 | TCU Acórdão 1947/2017",
  },
  T19: {
    description:
      "Detecta alternância sistemática de vencedores em licitações repetidas para os mesmos itens ou categorias: empresa A vence no mês 1, B no mês 2, A novamente no mês 3. Padrão estatisticamente improvável na ausência de coordenação prévia — indicador clássico de cartel em rodízio.",
    legal: "Lei 12.529/2011, Art. 36, III | Lei 14.133/2021, Arts. 337-F/G/H | CP Art. 335-A",
  },
  T20: {
    description:
      "Identifica empresas que participam como licitantes mas não possuem histórico operacional real: CNPJ registrado há menos de 30 dias antes do pregão, sem funcionários no eSocial, sem contratos anteriores e sem estabelecimento verificável. Serve como proxy para concorrência simulada.",
    legal: "Lei 14.133/2021, Art. 337-F | Lei 12.529/2011, Art. 36 | Lei 12.846/2013, Art. 5°, IV",
  },
  T21: {
    description:
      "Aplica análise de cluster estatístico a lances de um mesmo grupo de fornecedores em múltiplos certames: detecta coordenação implícita via similaridade de valor (coeficiente de variação < 5%), timing de submissão e padrão de retirada de proposta. Requer ao menos 5 licitações no janela de 12 meses.",
    legal: "Lei 12.529/2011, Arts. 36-38 | CADE Resolução 20/2017 | Lei 14.133/2021, Art. 155, IV",
  },
  T22: {
    description:
      "Cruza dados de doações eleitorais (TSE) com contratos firmados por órgãos vinculados ao mesmo poder/esfera nos 24 meses seguintes. Alta correlação temporal entre doação e contratação do mesmo CNPJ/grupo econômico indica possível retribuição clientelista.",
    legal: "CF/88, Art. 14, §9° | Lei 9.504/1997, Art. 81 | FATF Recomendação 12 | Lei 12.846/2013",
  },
};

export const TYPOLOGY_META: Record<string, { corruption_types: string[]; spheres: string[] }> = {
  T01: { corruption_types: ["fraude_licitatoria"],                          spheres: ["administrativa"] },
  T02: { corruption_types: ["fraude_licitatoria"],                          spheres: ["administrativa"] },
  T03: { corruption_types: ["fraude_licitatoria"],                          spheres: ["administrativa"] },
  T04: { corruption_types: ["fraude_licitatoria", "corrupcao_passiva"],     spheres: ["administrativa"] },
  T05: { corruption_types: ["fraude_licitatoria"],                          spheres: ["administrativa", "privada"] },
  T06: { corruption_types: ["lavagem", "corrupcao_ativa"],                  spheres: ["privada", "administrativa"] },
  T07: { corruption_types: ["fraude_licitatoria", "corrupcao_ativa"],       spheres: ["privada", "sistemica"] },
  T08: { corruption_types: ["corrupcao_passiva", "prevaricacao"],           spheres: ["administrativa"] },
  T09: { corruption_types: ["peculato"],                                    spheres: ["administrativa"] },
  T10: { corruption_types: ["peculato", "fraude_licitatoria"],              spheres: ["administrativa"] },
  T11: { corruption_types: ["fraude_licitatoria", "peculato"],              spheres: ["administrativa", "privada"] },
  T12: { corruption_types: ["fraude_licitatoria", "corrupcao_ativa_passiva"], spheres: ["administrativa"] },
  T13: { corruption_types: ["nepotismo_clientelismo", "corrupcao_ativa_passiva"], spheres: ["administrativa", "politica"] },
  T14: { corruption_types: ["corrupcao_ativa_passiva", "fraude_licitatoria"], spheres: ["administrativa", "sistemica"] },
  T15: { corruption_types: ["fraude_licitatoria", "prevaricacao"],          spheres: ["administrativa"] },
  T16: { corruption_types: ["nepotismo_clientelismo", "peculato"],          spheres: ["politica", "administrativa"] },
  T17: { corruption_types: ["lavagem"],                                     spheres: ["privada", "sistemica"] },
  T18: { corruption_types: ["peculato", "nepotismo_clientelismo"],          spheres: ["administrativa"] },
  T19: { corruption_types: ["fraude_licitatoria"],                          spheres: ["privada", "sistemica"] },
  T20: { corruption_types: ["fraude_licitatoria"],                          spheres: ["privada"] },
  T21: { corruption_types: ["fraude_licitatoria"],                          spheres: ["privada", "sistemica"] },
  T22: { corruption_types: ["nepotismo_clientelismo", "corrupcao_ativa_passiva"], spheres: ["politica", "privada"] },
};

export const COVERAGE_STATUS_LABELS: Record<string, string> = {
  ok: "Atualizado",
  warning: "Alerta",
  stale: "Desatualizado",
  error: "Erro",
  pending: "Pendente",
};

export const NAV_ITEMS = [
  { href: "/radar", label: "Radar", icon: "Radar" as const },
  { href: "/coverage", label: "Cobertura", icon: "Database" as const },
  { href: "/methodology", label: "Metodologia", icon: "BookOpen" as const },
  { href: "/api-health", label: "Saúde API", icon: "Activity" as const },
];

export const CORRUPTION_TYPE_LABELS: Record<string, string> = {
  fraude_licitatoria: "Fraude em Licitação",
  corrupcao_ativa_passiva: "Corrupção Ativa/Passiva",
  corrupcao_passiva: "Corrupção Passiva",
  corrupcao_ativa: "Corrupção Ativa",
  peculato: "Peculato",
  lavagem: "Lavagem de Dinheiro",
  prevaricacao: "Prevaricação",
  concussao: "Concussão",
  nepotismo_clientelismo: "Nepotismo/Clientelismo",
};

export const SPHERE_LABELS: Record<string, string> = {
  administrativa: "Administrativa",
  privada: "Privada",
  politica: "Política",
  sistemica: "Sistêmica",
};

export const CONNECTOR_COLORS: Record<string, { bg: string; text: string; ring: string }> = {
  pncp:                 { bg: "bg-blue-100",    text: "text-blue-800",    ring: "ring-blue-400" },
  compras_gov:          { bg: "bg-indigo-100",  text: "text-indigo-800",  ring: "ring-indigo-400" },
  comprasnet_contratos: { bg: "bg-sky-100",     text: "text-sky-800",     ring: "ring-sky-400" },
  portal_transparencia: { bg: "bg-amber-100",   text: "text-amber-800",   ring: "ring-amber-400" },
  transfere_gov:        { bg: "bg-orange-100",  text: "text-orange-800",  ring: "ring-orange-400" },
  tse:                  { bg: "bg-red-100",     text: "text-red-800",     ring: "ring-red-400" },
  receita_cnpj:         { bg: "bg-emerald-100", text: "text-emerald-800", ring: "ring-emerald-400" },
  camara:               { bg: "bg-purple-100",  text: "text-purple-800",  ring: "ring-purple-400" },
  senado:               { bg: "bg-violet-100",  text: "text-violet-800",  ring: "ring-violet-400" },
  querido_diario:       { bg: "bg-pink-100",    text: "text-pink-800",    ring: "ring-pink-400" },
};

export const CONNECTOR_LABELS: Record<string, string> = {
  pncp: "PNCP",
  compras_gov: "ComprasGov",
  comprasnet_contratos: "ComprasNet",
  portal_transparencia: "Portal da Transparência",
  transfere_gov: "TransfereGov",
  tse: "TSE",
  receita_cnpj: "Receita Federal",
  camara: "Câmara dos Deputados",
  senado: "Senado Federal",
  querido_diario: "Querido Diário",
};

export const DATA_SOURCES = [
  "Portal da Transparência",
  "Compras.gov.br",
  "ComprasNet Contratos",
  "PNCP",
  "Transfere.gov",
  "Câmara dos Deputados",
  "Senado Federal",
  "TSE",
  "Receita Federal (CNPJ)",
  "Querido Diário",
];
