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
