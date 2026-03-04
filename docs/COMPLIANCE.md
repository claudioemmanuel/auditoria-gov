# Compliance & Responsabilidade Legal — AuditorIA Gov

**Versão:** 1.0
**Data de vigência:** 2026-03-04
**Revisão:** Trimestral

---

## 1. Status Legal — O que a plataforma faz e por que é legal

O AuditorIA Gov é uma plataforma de auditoria cidadã que **coleta, processa e apresenta exclusivamente dados já tornados públicos por força de lei**. Nenhum dado é obtido por meio de acesso não autorizado, violação de sigilo ou qualquer método ilícito.

A operação da plataforma está fundamentada em quatro eixos:

| Pilar | O que significa |
|-------|-----------------|
| **Tecnologicamente robusto** | Domain guard com whitelist governamental, testes automatizados, código aberto (AGPL-3.0), cadeia de proveniência auditável |
| **Metodologicamente defensável** | Tipologias com base legal explícita, scoring determinístico e reproduzível, veracity registry público |
| **Juridicamente responsável** | Opera sobre dados de transparência ativa obrigatória — CF/88, LAI, LGPD, Lei Anticorrupção |
| **Publicamente auditável** | Open source, endpoints de proveniência públicos, `GET /public/sources` expõe toda a cadeia |

**A plataforma não acusa. Produz sinais investigáveis** para controle social e auditoria cidadã, com aviso explícito em cada sinal: *"indicador estatístico, não acusação"*.

---

## 2. Fundamentos Constitucionais

### CF/88, art. 5º, XXXIII
> *"todos têm direito a receber dos órgãos públicos informações de seu interesse particular, ou de interesse coletivo ou geral, que serão prestadas no prazo da lei, sob pena de responsabilidade, ressalvadas aquelas cujo sigilo seja imprescindível à segurança da sociedade e do Estado"*

**Aplicação:** Qualquer cidadão tem direito às informações que a plataforma coleta e analisa.

### CF/88, art. 37, caput (Princípio da Publicidade)
O princípio da publicidade da Administração Pública impõe que os atos administrativos sejam acessíveis ao público. A plataforma exerce o papel de amplificador desse princípio, tornando os dados acessíveis de forma estruturada e analisável.

### CF/88, art. 74, §1º
> *"Qualquer cidadão, partido político, associação ou sindicato é parte legítima para, na forma da lei, denunciar irregularidades ou ilegalidades perante o Tribunal de Contas da União."*

**Aplicação:** A plataforma fornece insumos técnicos para que qualquer cidadão exerça esse direito constitucional.

---

## 3. Lei de Acesso à Informação (LAI)

**Lei 12.527/2011 + Decreto 7.724/2012** — Regulamentam a transparência ativa obrigatória.

### Dados de transparência ativa que a plataforma consome

| Dado | Base Legal |
|------|-----------|
| Licitações e contratos | LAI art. 8º, §1º, IV + Decreto 7.724/2012 art. 7º, IV |
| Despesas e execução orçamentária | LAI art. 8º, §1º, III |
| Remuneração de servidores | LAI art. 8º, §1º, VII |
| Benefícios sociais (BPC, Bolsa Família etc.) | LAI art. 8º, §1º, III |
| Viagens a serviço | LAI art. 8º, §1º, VII |
| Cartão de pagamento governamental | LAI art. 8º, §1º, III |
| Emendas parlamentares | LAI art. 8º + EC 105/2019 |
| Convênios e transferências | LAI art. 8º, §1º, IV |
| Candidatos e contas eleitorais | Lei 9.504/97 art. 28 + Res. TSE 23.604 |
| CNPJ e quadro societário | Lei 8.934/94 art. 29 (dados públicos do cadastro empresarial) |
| Diários oficiais | Constituição Federal, art. 37 (publicidade) |

Todos esses dados são de **divulgação ativa obrigatória** — as entidades governamentais são legalmente obrigadas a publicá-los. A plataforma apenas os organiza, cruza e analisa.

---

## 4. LGPD — Proteção de Dados Pessoais

**Lei 13.709/2018 (LGPD)**

### 4.1 Base Legal Aplicável

| Dispositivo | Conteúdo | Aplicação |
|-------------|----------|-----------|
| Art. 7º, VI | Exercício regular de direitos em processo judicial, administrativo ou arbitral | Análise de irregularidades e suporte a denúncias ao TCU/CGU/MPF |
| Art. 7º, VII | Proteção da vida ou incolumidade física | — |
| Art. 7º, III | Cumprimento de obrigação legal ou regulatória | Dados já publicados por obrigação legal |
| Art. 23, I | Tratamento por pessoa jurídica de direito público | Dados oriundos de órgãos públicos com base legal |
| Art. 12 | Anonimização | CPFs são hasheados e nunca persistidos em claro |

### 4.2 Tratamento de CPF

- CPFs coletados de bases públicas são imediatamente hasheados via `shared/utils/hashing.py` com salt configurado por variável de ambiente (`CPF_HASH_SALT`)
- O valor original do CPF **nunca é armazenado** em nenhuma tabela do banco de dados
- O hash é unidirecional (SHA-256 + salt) — não é reversível sem o salt
- Esta implementação está em conformidade com o art. 12 da LGPD (dados anonimizados não são considerados dados pessoais)

### 4.2b Escopo LGPD na Busca de Entidades

A funcionalidade `GET /public/entity/search` aplica escopos automáticos de proteção à privacidade:

| Tipo | Restrição |
|------|-----------|
| Empresa (CNPJ) | Sem restrição — CNPJ é dado público por lei (Lei 8.934/94, art. 29) |
| Pessoa física | Restrita a servidores e funcionários públicos identificados via `EntityRawSource.source_connector` (ex.: `pt_servidores_remuneracao`, `pt_ceis_cnpj`) |

Pessoas físicas não oriundas de conectores de servidores públicos são excluídas dos resultados. CPF **nunca aparece na resposta** — validado por teste de regressão LGPD (`assert "cpf" not in json.dumps(response.json())`).

### 4.3 Dados de Servidores Públicos

O Supremo Tribunal Federal (STF), no RE 652.777 (repercussão geral), fixou a seguinte tese:

> *"É legítima a publicação, inclusive em sítio eletrônico mantido pela Administração Pública, dos nomes dos seus servidores e do valor dos correspondentes vencimentos e vantagens pecuniárias."*

A divulgação de remuneração de servidores públicos é constitucionalmente legítima.

---

## 5. Plano de Compliance Contínuo

O compliance da plataforma é verificado automaticamente de forma contínua e documentada.

### 5.1 Auditoria Semanal Automatizada

Toda segunda-feira às 06:00 UTC, a tarefa `check_source_compliance` executa:

1. **Validação de domínio** — Verifica que todas as URLs de conectores estão na whitelist governamental (`.gov.br`, `.jus.br`, `.leg.br`, `.mil.br`, `.mp.br`, `.def.br`)
2. **Verificação de exceções** — Alerta 30 dias antes do vencimento de qualquer exceção de domínio aprovada
3. **Probe de disponibilidade** — HTTP HEAD em cada fonte; fontes inacessíveis são marcadas como `warning`
4. **Atualização do registro** — `coverage_registry.compliance_status` atualizado para `ok`, `warning` ou `violation`

### 5.2 Status de Compliance

| Status | Significado |
|--------|------------|
| `ok` | Domínio na whitelist, API acessível |
| `warning` | API inacessível ou exceção prestes a expirar |
| `violation` | Domínio fora da whitelist (não deve ocorrer em produção) |

### 5.3 Revisão Trimestral

A cada trimestre, são revisados:
- Todas as exceções de domínio (`DomainException.review_by`)
- Perfis de veracidade das fontes (`SourceVeracityProfile`)
- Relevância das tipologias frente a mudanças legislativas
- Adequação das bases legais citadas

### 5.4 Resultado da Última Auditoria

O status em tempo real de cada fonte de dados está disponível em:

```
GET /public/sources
```

Este endpoint público expõe, para cada conector:
- Score de veracidade (5 critérios + score composto)
- Status de compliance (`ok` / `warning` / `violation`)
- Data da última verificação
- Tier de domínio (governamental / exceção controlada)

---

## 6. O que a plataforma NÃO faz

É fundamental deixar claro o que a plataforma **não realiza**:

| O que NÃO faz | Motivo |
|---------------|--------|
| ❌ Acusa pessoas ou empresas | Sinais são hipóteses estatísticas, não provas |
| ❌ Armazena dados pessoais além do necessário | Minimização de dados conforme LGPD art. 6º, III |
| ❌ Persiste CPFs em texto claro | CPFs são hasheados imediatamente conforme LGPD art. 12 |
| ❌ Acessa dados sigilosos ou restritos | Opera apenas sobre transparência ativa obrigatória |
| ❌ Usa IA para gerar scores ou acusações | LLM é exclusivamente explicativo; scores são determinísticos |
| ❌ Conclui culpabilidade | Produz sinais de risco para investigação, não julgamento |
| ❌ Coleta dados de fontes não autorizadas | Domain guard bloqueia domínios fora da whitelist em nível de HTTP |

---

## 7. Mecanismos de Contestação

Qualquer entidade (pessoa física ou jurídica) que apareça em um sinal da plataforma pode:

1. **Consultar a proveniência** — `GET /signal/{id}/provenance` expõe todos os dados brutos que geraram o sinal
2. **Verificar a metodologia** — A lógica de cada tipologia está documentada em `/methodology` e no código-fonte aberto
3. **Contestar o sinal** — `GET /contestation` (endpoint de mecanismo de contestação) permite registrar impugnação formal
4. **Acessar o código** — O código-fonte é aberto (AGPL-3.0) e qualquer técnico pode verificar os cálculos

**A plataforma não constitui processo judicial ou administrativo.** A contestação aqui se refere a sinalizações incorretas por erro de dados, não a processos legais, que devem seguir as vias próprias.

---

## 8. Responsabilidade Editorial

### 8.1 Aviso Obrigatório

Todos os sinais emitidos pela plataforma carregam o seguinte aviso:

> *"Este resultado representa um indicador estatístico para triagem e controle social. Não configura acusação, prova definitiva ou juízo de culpa. A verificação adicional por autoridade competente é necessária antes de qualquer conclusão."*

### 8.2 Sinal ≠ Prova

A distinção fundamental da plataforma:

- **Sinal de risco** = padrão estatístico anômalo nos dados públicos disponíveis
- **Prova** = elemento de convicção que satisfaz critérios processuais legais

A plataforma produz sinais, nunca provas. Provas são produzidas por investigações conduzidas por autoridades competentes (CGU, TCU, MPF, PGR, Polícia Federal).

### 8.3 Limitações Conhecidas

- Dados retroativos dependem da qualidade das APIs governamentais
- Fontes com latência ou indisponibilidade são identificadas no painel de cobertura
- Tipologias estatísticas têm taxa natural de falsos positivos, que é documentada por tipologia

---

## Referências

- [Constituição Federal de 1988](https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm)
- [Lei 12.527/2011 (LAI)](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm)
- [Decreto 7.724/2012](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/decreto/d7724.htm)
- [Lei 13.709/2018 (LGPD)](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [Lei 12.846/2013 (Lei Anticorrupção)](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12846.htm)
- [Lei 8.429/1992 (Improbidade Administrativa)](https://www.planalto.gov.br/ccivil_03/leis/l8429.htm)
- [Lei 14.133/2021 (Nova Lei de Licitações)](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/L14133.htm)
- [STF — RE 652.777 (Publicidade de remuneração)](https://portal.stf.jus.br/jurisprudencia/sumariosumula.asp?base=acordaos&docid=RE%20652777)
- [docs/GOVERNANCE.md](./GOVERNANCE.md) — Política de integridade de fontes e veracidade
