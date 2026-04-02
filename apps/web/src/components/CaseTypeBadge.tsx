const CASE_TYPE_LABELS: Record<string, { label: string; className: string }> = {
  CARTEL_NETWORK: { label: 'Rede de Cartel', className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' },
  CONFLICT_OF_INTEREST: { label: 'Conflito de Interesse', className: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400' },
  DIRECTED_TENDER: { label: 'Edital Direcionado', className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' },
  PROCUREMENT_FRAUD: { label: 'Fraude Licitatória', className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' },
  SANCTIONED_ENTITY: { label: 'Entidade Sancionada', className: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400' },
  MONEY_LAUNDERING_PROXY: { label: 'Lavagem', className: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400' },
  ILLEGAL_ACCUMULATION: { label: 'Acúmulo Ilegal', className: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400' },
  COMPOUND_FAVORITISM: { label: 'Favorecimento Composto', className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' },
  HIGH_RISK_COMPOUND: { label: 'Risco Composto', className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' },
};

interface Props {
  caseType: string | null | undefined;
}

export function CaseTypeBadge({ caseType }: Props) {
  if (!caseType || caseType === 'OTHER') return null;
  const config = CASE_TYPE_LABELS[caseType];
  if (!config) return null;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}
