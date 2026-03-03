# Deteccao de Corrupcao por Tipos e Esferas - Legal First

Data de corte: **2026-03-02**  
Escopo: enquadramento juridico-pratico para orientar o motor analitico e a comunicacao em produto.

## 1) Objetivo juridico-operacional

Definir um marco legal claro para que o app:
- gere **sinais de risco** (nao juizo de culpa),
- mantenha **rastreabilidade probatoria**,
- reduza risco de falsa imputacao,
- alinhe a analise tecnica com comunicacao segura em UI/UX.

Principio central:
- o sistema aponta **hipotese investigativa**; a decisao juridica pertence a controle interno, auditoria, corregedoria, MP e Judiciario.

## 2) Tipos de corrupcao e base legal

## 2.1 Corrupcao ativa
- Base: art. 333 do Codigo Penal.
- Conduta: oferecer/prometer vantagem indevida a agente publico.
- Sinais indiretos tipicos: cadeia de favorecimento contratual, padrao recorrente de vencedor vinculado, intermediacao opaca.

## 2.2 Corrupcao passiva
- Base: art. 317 do Codigo Penal.
- Conduta: solicitar/receber/aceitar promessa de vantagem indevida.
- Sinais indiretos tipicos: ato decisorio anomalo com beneficiario recorrente, ganho indireto de terceiro conectado.

## 2.3 Concussao
- Base: art. 316 do Codigo Penal.
- Conduta: exigir vantagem indevida valendo-se da funcao.
- Sinais indiretos tipicos: bloqueio-liberacao administrativo fora de padrao, clusters de denuncia convergente.

## 2.4 Prevaricacao
- Base: art. 319 do Codigo Penal.
- Conduta: retardar/omitir/agir contra lei por interesse pessoal.
- Sinais indiretos tipicos: atraso seletivo de processo, inversao de fila sem justificativa.

## 2.5 Peculato
- Base: art. 312 do Codigo Penal.
- Conduta: apropriacao/desvio/subtracao de recursos ou bens publicos.
- Sinais indiretos tipicos: pagamento sem lastro, folha fantasma, sobreposicao funcional em terceirizacao.

## 2.6 Lavagem de dinheiro
- Base: Lei 9.613/1998.
- Conduta: ocultacao/dissimulacao da origem ilicita de ativos.
- Sinais indiretos tipicos: layering societario, empresas de passagem, fluxo circular sem racional economico.

## 2.7 Fraude em licitacao / conluio / sobrepreco
- Base: Lei 14.133/2021 + Lei 12.846/2013 (responsabilizacao empresarial).
- Conduta: manipulacao de competitividade e/ou preco.
- Sinais indiretos tipicos: rodizio de vencedores, propostas espelho, sobrepreco persistente.

## 2.8 Nepotismo e clientelismo
- Base: Decreto 7.203/2010 (nepotismo no Executivo Federal), jurisprudencia e controle administrativo.
- Conduta: nomeacao/beneficio por laco pessoal-politico indevido.
- Sinais indiretos tipicos: nomeacoes cruzadas, contratos ligados a rede familiar-politica.

## 3) Esferas de corrupcao (efeito pratico na deteccao)

## 3.1 Politica (macro)
- foco em contratos de alto valor, emendas e captura de decisao publica.

## 3.2 Administrativa/burocratica
- foco em execucao cotidiana: licitacao, contrato, despesa, folha, sancao.

## 3.3 Privada
- foco em suborno entre privados, fraude corporativa e conluio com setor publico.

## 3.4 Sistemica
- foco em recorrencia estrutural de redes e baixa efetividade sancionatoria.

## 4) Regra juridica de linguagem no produto

Obrigatorio em UI/UX e API de saida:
- usar: "sinal", "indicio", "hipotese investigativa".
- evitar: "culpado", "corrupto", "crime comprovado" (sem decisao final).

Rotulo de status de caso:
- `finalizado`: sancao/decisao definitiva.
- `em andamento`: investigacao/PAR/inquerito/acao sem transito.

## 5) LGPD + LAI: limites para exibicao

- LGPD (Lei 13.709/2018): minimizacao, finalidade, necessidade e seguranca.
- LAI (Lei 12.527/2011): transparencia ativa de dados publicos.
- Convergencia pratica: publicar evidencias relevantes sem expor dado pessoal desnecessario.

Controles obrigatorios:
- trilha de proveniencia (`source_hash`, `captured_at`, `snapshot_uri`),
- direito de contestacao,
- possibilidade de retificacao,
- reducao de risco de homonimia em vinculos pessoais.

## 6) Matriz legal -> exigencia de prova tecnica

| Tipo | Exigencia minima para sinal robusto | Risco juridico se faltar |
|---|---|---|
| Corrupcao ativa/passiva | cadeia de evento + vinculo relacional + anomalia objetiva | inferencia excessiva de intencao |
| Concussao | padrao temporal + evidencia de coercao (denuncia/log) | confundir ineficiencia com extorsao |
| Prevaricacao | SLA normativo + atraso seletivo comprovavel | confundir backlog com dolo |
| Peculato | inconsistencia contabil + ausencia de lastro | confundir erro operacional com desvio |
| Lavagem | estrutura de ocultacao (camadas/fluxo) | confundir planejamento legitimo com ilicito |
| Fraude licitatoria | padrao de cartel/sobrepreco estatisticamente consistente | confundir mercado concentrado com conluio |
| Nepotismo/clientelismo | vinculo pessoal-politico verificavel + beneficio administrativo | falso positivo por homonimo/vinculo fraco |

## 7) Como o legal-first orienta o engineer-first

Regras de acoplamento:
- cada tipologia tecnica deve explicitar qual tipo/esfera juridica cobre;
- severidade alta/critica exige evidencias independentes multiplas;
- completar sinal sem evidencias suficientes deve reduzir severidade automaticamente;
- sempre expor no frontend a completude da evidencia e janela temporal.

## 8) Referencias primarias

- Codigo Penal (DL 2.848/1940): https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm
- Lei 9.613/1998 (Lavagem): https://www.planalto.gov.br/ccivil_03/leis/l9613.htm
- Lei 14.133/2021 (Licitacoes): https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm
- Lei 12.846/2013 (Anticorrupcao): https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12846.htm
- Decreto 11.129/2022: https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2022/decreto/d11129.htm
- Decreto 7.203/2010 (Nepotismo): https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/decreto/d7203.htm
- LGPD: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- LAI: https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm
- TCU Referencial de Combate a Fraude e Corrupcao: https://portal.tcu.gov.br/data/files/8A/15/80/74/B5976910EC522198F18818A8/Referencial%20de%20Combate%20a%20Fraude%20e%20Corrupcao.pdf
- OECD Bid Rigging Guidelines (2025): https://www.oecd.org/en/publications/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025_4d7c385c-en.html
- CADE Guia de Cartel em Licitacoes: https://cdn.cade.gov.br/Portal/centrais-de-conteudo/publicacoes/guias-do-cade/guia_analise_cartel_licitacoes_publicas.pdf
- FATF - Laundering the Proceeds of Corruption: https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Laundering-the-Proceeds-of-Corruption.pdf.coredownload.inline.pdf

## 9) Resultado esperado para produto

Quando um usuario visualizar um sinal, ele deve entender:
1. qual hipotese juridica esta sendo sugerida,
2. quais evidencias sustentam a sugestao,
3. qual o nivel de completude/confianca,
4. que aquilo nao equivale a condenacao.

Este contrato legal e a base para o documento engineer-first e para o comparativo com a implementacao atual.
