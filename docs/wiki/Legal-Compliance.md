# Conformidade Legal & Compliance

Esta página responde às dúvidas mais comuns sobre a legalidade do AuditorIA Gov e detalha o respaldo jurídico que sustenta a plataforma.

Para o documento técnico-jurídico completo, consulte [docs/COMPLIANCE.md](../COMPLIANCE.md).

---

## Em uma linha

> O AuditorIA Gov analisa **exclusivamente dados já tornados públicos por força de lei** (LAI, CF/88, legislação eleitoral e registros empresariais), os organiza de forma investigável e exibe sinais de risco com aviso de que são hipóteses estatísticas, não provas.

---

## Os Quatro Pilares de Responsabilidade

| Pilar | O que significa na prática |
|-------|---------------------------|
| **Tecnologicamente robusto** | Whitelist de domínios governamentais (`.gov.br`, `.leg.br` etc.), testes automatizados, código aberto AGPL-3.0, cadeia de proveniência rastreável de cada dado |
| **Metodologicamente defensável** | 22 tipologias com base legal explícita, scoring determinístico e reproduzível, nenhuma IA na geração de scores |
| **Juridicamente responsável** | Opera sobre transparência ativa obrigatória — CF/88 art. 5º XXXIII, LAI, LGPD art. 7º VI, Lei Anticorrupção |
| **Publicamente auditável** | Código-fonte aberto, `GET /public/sources` expõe todas as fontes e scores de veracidade, metodologia documentada |

---

## Respaldo Legal

### Constituição Federal

| Dispositivo | Conteúdo relevante |
|-------------|-------------------|
| Art. 5º, XXXIII | Direito de qualquer cidadão obter informações de órgãos públicos |
| Art. 37, caput | Princípio da Publicidade da Administração Pública |
| Art. 74, §1º | Qualquer cidadão pode denunciar irregularidades ao TCU |

### Lei de Acesso à Informação (LAI)

A [Lei 12.527/2011](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm) e o [Decreto 7.724/2012](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/decreto/d7724.htm) **obrigam** os órgãos públicos a publicar ativamente:

- Licitações, contratos e despesas (art. 8º, §1º, III e IV)
- Remuneração de servidores (art. 8º, §1º, VII)
- Benefícios sociais e transferências (art. 8º, §1º, III)

A plataforma consome essas publicações obrigatórias.

### LGPD

A [Lei 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) permite o tratamento de dados no contexto desta plataforma por:

- **Art. 7º, VI** — Exercício regular de direitos (suporte a denúncias ao TCU/CGU/MPF)
- **Art. 12** — CPFs são hasheados (SHA-256 + salt) e nunca persistidos em claro; dados anonimizados não são considerados dados pessoais pela LGPD

O STF, no RE 652.777, fixou que a publicação de remuneração de servidores públicos é constitucionalmente legítima.

### Leis de Combate à Corrupção

| Lei | Relevância |
|-----|-----------|
| [Lei 12.846/2013 (Anticorrupção)](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12846.htm) | Fundamenta a detecção de irregularidades que a plataforma identifica |
| [Lei 8.429/1992 (Improbidade)](https://www.planalto.gov.br/ccivil_03/leis/l8429.htm) | Base normativa de tipologias de peculato, enriquecimento ilícito e fraude |
| [Lei 14.133/2021 (Licitações)](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/L14133.htm) | Fundamenta T01–T08 (concentração, conluio, fracionamento etc.) |
| [Lei 9.613/1998 (Lavagem de Dinheiro)](https://www.planalto.gov.br/ccivil_03/leis/l9613.htm) | Crimes de lavagem e ocultação de bens — base de T17 |
| [Lei 12.529/2011 (Defesa da Concorrência)](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12529.htm) | Cartel e conluio em licitações — base de T07 e T19–T21 |
| CF/88 Art. 166-A + EC 105/2019 | Emendas parlamentares Pix — base de T16 |

---

## LGPD e Busca de Entidades

A funcionalidade de busca de entidades (`GET /public/entity/search`) aplica escopos LGPD automáticos:

- **Empresas (CNPJ)** — sem restrição; CNPJ é dado público por lei (Lei 8.934/94).
- **Pessoas físicas** — restritas a servidores e funcionários públicos identificados via `EntityRawSource` (join com `source_connector IN ('pt_servidores_remuneracao', 'pt_servidores_licencas', …)`). Pessoas não oriundas de fontes de transparência ativa de servidores são excluídas dos resultados.
- **CPF nunca aparece na resposta** — confirmado por teste de regressão LGPD na suíte de testes.

## FAQ Rápido

**Vocês estão violando a LGPD?**
Não. O tratamento tem base legal no art. 7º, VI da LGPD. Dados pessoais (CPF) são anonimizados conforme art. 12. A busca de pessoas retorna apenas servidores públicos.

**Podem publicar dados de servidores públicos?**
Sim. O STF (RE 652.777) e a LAI (art. 8º, §1º, VII) garantem a legitimidade dessa publicação.

**Um servidor público pode me processar por usar a plataforma?**
A análise de dados de transparência ativa é exercício de direito constitucional (CF/88 art. 5º, XXXIII e XXXIV). Consulte um advogado para situações específicas.

**Quem pode usar os dados desta plataforma?**
Qualquer pessoa — cidadãos, jornalistas, advogados, auditores, pesquisadores e órgãos de controle.

**Como contestar um sinal que me afeta?**
Consulte `GET /signal/{id}/provenance` para verificar os dados brutos e `POST /contestation` para registrar impugnação.

---

## Comparativo com outras plataformas de controle social

| Plataforma | Abordagem | Base legal |
|------------|-----------|-----------|
| **AuditorIA Gov** | Detecção determinística + scoring + proveniência | LAI + CF/88 + LGPD |
| Transparência Internacional | Rankings e relatórios | Dados públicos + pesquisa |
| Operação Serenata de Amor | Fiscalização de cotas parlamentares | LAI + dados da Câmara |
| Brasil.io | Agregador de dados públicos estruturados | LAI |

---

## Links úteis

- [docs/COMPLIANCE.md](../COMPLIANCE.md) — Documento técnico-jurídico completo
- [docs/GOVERNANCE.md](../GOVERNANCE.md) — Política de integridade de fontes e veracidade
- [GET /public/sources](#) — Status em tempo real de todas as fontes
- [/methodology](/methodology) — Metodologia técnica das tipologias
