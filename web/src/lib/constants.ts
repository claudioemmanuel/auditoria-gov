export const SEVERITY_LABELS: Record<string, string> = {
  low: "Baixo",
  medium: "Medio",  // TODO: "Médio" when accent support confirmed
  high: "Alto",
  critical: "Critico",
};

export const TYPOLOGY_LABELS: Record<string, string> = {
  T01: "Concentracao em Fornecedor",
  T02: "Baixa Competicao",
  T03: "Fracionamento de Despesa",
  T04: "Aditivo Outlier",
  T05: "Preco Outlier",
  T06: "Proxy de Empresa de Fachada",
  T07: "Rede de Cartel",
  T08: "Sancao x Contrato",
  T09: "Proxy de Folha Fantasma",
  T10: "Terceirizacao Paralela",
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
];

export const CORRUPTION_TYPE_LABELS: Record<string, string> = {
  fraude_licitatoria: "Fraude em Licitacao",
  corrupcao_passiva: "Corrupcao Passiva",
  corrupcao_ativa: "Corrupcao Ativa",
  peculato: "Peculato",
  lavagem: "Lavagem de Dinheiro",
  prevaricacao: "Prevaricacao",
  concussao: "Concussao",
  nepotismo_clientelismo: "Nepotismo/Clientelismo",
};

export const SPHERE_LABELS: Record<string, string> = {
  administrativa: "Administrativa",
  privada: "Privada",
  politica: "Politica",
  sistemica: "Sistemica",
};

export const DATA_SOURCES = [
  "Portal da Transparencia",
  "Compras.gov.br",
  "ComprasNet Contratos",
  "PNCP",
  "Transfere.gov",
  "Camara dos Deputados",
  "Senado Federal",
  "TSE",
  "Receita Federal (CNPJ)",
  "Querido Diario",
];
