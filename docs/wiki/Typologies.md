# Typologies

The typology engine runs deterministic detectors registered in `shared/typologies/registry.py`.

For full legal framework details (article numbers, TCU/CGU jurisprudence, thresholds), see:
- [T01-T10 Legal Matrix](../plans/2026-03-04-typology-legal-matrix.md)
- [T11-T18 New Typologies Proposals](../plans/2026-03-04-new-typologies-proposals.md)

## T01-T10 — Implemented Typologies

| Code | Typology | Legal Basis | Evidence Level |
|---|---|---|---|
| T01 | Supplier concentration (HHI) | Lei 14.133/2021, Art. 11 | indirect |
| T02 | Low competition | Lei 14.133/2021, Art. 11, I | indirect |
| T03 | Expense splitting (fracionamento) | Lei 14.133/2021, Art. 75, § 1°; **Decreto 12.343/2024** | direct |
| T04 | Amendment outlier (aditivos) | Lei 14.133/2021, Art. 125; Lei 8.666/93, Art. 65, § 1° | indirect |
| T05 | Price outlier (sobrepreço) | Lei 14.133/2021, Art. 92; TCU Acórdão 1875/2021 | direct |
| T06 | Shell company proxy | Lei 12.846/2013, Art. 5°, IV; TCU Acórdão 1798/2024 | proxy |
| T07 | Cartel network | Lei 12.529/2011, Art. 36; Lei 14.133/2021, Arts. 337-F/G/H | indirect |
| T08 | Sanctions mismatch (CEIS/CNEP) | Lei 14.133/2021, Art. 68; Lei 12.846/2013, Art. 22 | direct |
| T09 | Ghost payroll proxy | CP Art. 312 (peculato); TCU Acórdão 1947/2017 | proxy |
| T10 | Outsourcing + parallel payroll | Lei 6.019/1974; Lei 14.133/2021, Arts. 117-121 | indirect |

### T03 Threshold Note
Dispensa de licitação thresholds were updated by **Decreto 12.343/2024**:
- Bens e serviços: **R$ 62.725,59** (was R$ 50.000)
- Obras e engenharia: **R$ 125.451,15** (was R$ 100.000)

## T11-T18 — New Typologies (2026-03-04)

| Code | Typology | Priority | Legal Basis | Evidence Level |
|---|---|---|---|---|
| T11 | Jogo de planilha | P0 | Lei 14.133/2021, Arts. 92, 155; CGU Guia Superfaturamento 2025, Tipo 4 | direct |
| T12 | Edital direcionado | P0 | Lei 14.133/2021, Art. 9°, IV; Lei 8.666/93, Art. 3°, § 1° | indirect |
| T13 | Conflito de interesses | P0 | Lei 12.813/2013, Arts. 5°-6°; Decreto 7.203/2010; TCU Acórdão 1798/2024 | indirect |
| T14 | Sequência de favorecimento (meta) | P0 | CP Arts. 317/333; Lei 12.846/2013, Art. 5° | indirect |
| T15 | Inexigibilidade indevida | P1 | Lei 14.133/2021, Art. 74; Lei 8.429/92, Art. 10, VII | indirect |
| T16 | Clientelismo orçamentário-contratual | P1 | CF/88 Art. 166-A; TCU Acórdão 518/2023; STF Dino 2024 | indirect |
| T17 | Lavagem via camadas societárias | P1 | Lei 9.613/1998, Art. 1°; FATF Recomendação 24 | indirect |
| T18 | Acúmulo ilegal de cargos | P1 | CF/88 Art. 37, XVI-XVII; Lei 8.112/1990, Arts. 118-120 | direct |

## Detector Quality Expectations

- Numeric factors and transparent thresholds
- Reproducible evidence linked to raw/canonical records
- Test coverage for minimum-detectable scenarios
- Deterministic outputs for the same input data
- Legal basis documented per typology (see legal matrix docs above)
