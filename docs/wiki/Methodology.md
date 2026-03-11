# Methodology — AuditorIA Gov

This document describes the technical methodology of the AuditorIA Gov detection pipeline. It is intended for journalists, auditors, researchers, and anyone who wants to understand or verify how risk signals are generated.

For the legal compliance framework, see [Legal Compliance](./Legal-Compliance). For implementation details, see [docs/ARCHITECTURE.md](../ARCHITECTURE.md).

---

## 1. Detection Pipeline Overview

Risk signals are produced by a sequential, deterministic pipeline:

```
Ingestion → Normalization → Entity Resolution → Baselines → Signals → Coverage
```

| Stage | What happens |
|-------|-------------|
| **Ingestion** | Raw data is pulled from 11 public government sources and stored as immutable JSON payloads (`RawSource`). |
| **Normalization** | Raw payloads are mapped to canonical entities, events, and participant links. Each record preserves its `EventRawSource` link to the original payload. |
| **Entity Resolution (ER)** | Entities are matched and clustered across sources using name similarity, CNPJ/CPF hash, and shared identifiers. ER runs as a global singleton (advisory-locked). |
| **Baselines** | Statistical reference values are computed per entity and connector (e.g., average contract value, typical bidder count). These anchor anomaly detection in typologies. |
| **Signals** | Typology detectors (T01–T22) query canonical data and emit `RiskSignal` records with numeric factors, severity, and confidence. |
| **Coverage** | Freshness and completeness metrics are updated per source in the `coverage_registry`. |

---

## 2. Deterministic Scoring — No Machine Learning

All risk scoring is **deterministic and rule-based**. There is no machine learning, neural network, or probabilistic classifier in the scoring path.

Each typology produces:

| Field | Description |
|-------|-------------|
| `severity` | `low` / `medium` / `high` / `critical` — derived from numeric thresholds defined in the typology |
| `confidence` | 0.0–1.0 — proportion of corroborating evidence factors present |
| `factors` | JSON object with named numeric values (e.g., `{"ratio": 1.23, "window_days": 2}`) |
| `explanation_md` | Optional LLM-generated narrative — **display only, does not affect scoring** |

The same input data will always produce the same signal. This is a design requirement, not an accident.

---

## 3. Temporal Windows

All typology detectors use a **minimum 5-year lookback window** to capture Brazilian government data that was published retroactively (PNCP historical baseline starts at 2021).

Shorter windows (1–2 years) were found to miss the majority of available procurement records. The 5-year floor is a technical requirement, not a policy choice.

---

## 4. Evidence Chain (Provenance)

Every signal is fully traceable to its raw source data:

```
RiskSignal
  → SignalEvent  → Event → EventRawSource → RawSource (raw_data JSONB)
  → SignalEntity → Entity → EntityRawSource → RawSource
```

The `GET /signal/{id}/provenance` endpoint exposes this chain publicly. Any citizen can verify which raw API response generated a given signal.

---

## 5. False Positive Rates by Typology

Typologies vary significantly in their false positive characteristics. Users of the radar should be aware:

| Typology | False Positive Rate | Why |
|----------|--------------------|----|
| T02 (Low competition) | **High** — ~300 signals per 300 dispensa licitações | All dispensa procurement has 0 bidders by definition; signals are expected and low-actionability |
| T03 (Expense splitting) | **Low** — 3 real signals per 300 dispensa records | Requires tight temporal clustering + threshold proximity; high specificity |
| T08 (Sanctions mismatch) | **Medium** — depends on sanction data quality | Indefinite sanctions (no end date) are treated as still-active, which may include superseded sanctions |
| T14 (Compound favoritism) | **Depends on wave 1** — meta-typology reading from other signals | Only fires when multiple T01–T13 signals accumulate for the same entity |
| T19–T22 | **Calibration in progress** — advanced detection typologies | Statistical clustering methods; evidence level is `indirect` or `proxy` |

The disclaimer on every signal ("indicador estatístico, não acusação") reflects these known limitations.

---

## 6. Source Veracity and Score Penalty

Each data source has a **veracity score** (0.0–1.0) derived from 5 criteria:

| Criterion | Weight |
|-----------|--------|
| Government domain (`.gov.br`, `.leg.br` etc.) | 40% |
| Legal authority to publish | 25% |
| Public availability (no restricted credentials) | 15% |
| Official API documentation | 10% |
| Metadata and traceability | 10% |

Sources below `0.70` are labeled `low`. Signals derived **exclusively** from low-veracity sources receive a confidence penalty. The Querido Diário connector (score ~0.435) is the only `low` source currently active; no critical typology depends on it exclusively.

The full table is exposed at `GET /public/sources`.

---

## 7. What the AI Does and Does Not Do

| What the AI does | What the AI does NOT do |
|-----------------|------------------------|
| Generates narrative explanations in plain language (`explanation_md`) | Set `severity`, `confidence`, or any numeric factor |
| Provides context from legal text when available | Create, suppress, or modify risk signals |
| Summarizes evidence for readability | Participate in entity resolution or clustering |

All AI functions are decorated with `@explanatory_only` (enforced at runtime). The decorator raises `TypeError` if a non-string value is returned. Every invocation is logged as an audit event.

---

## 8. Known Limitations

| Limitation | Impact |
|-----------|--------|
| Government API quality varies | Some sources have gaps, stale data, or undocumented schema changes |
| PNCP data starts at 2021 | Historical signals before 2021 are not available for procurement typologies |
| ER is not perfect | Some distinct entities may share a cluster (false merge); some aliases may remain unlinked (false split) |
| Electoral contribution data is annual | T22 (political favoritism) can only detect year-level correlations, not intra-year timing |
| Querido Diário coverage is uneven | Municipal gazette coverage varies by state/municipality; gaps are not flagged per municipality |
| No real-time ingestion | Data freshness depends on connector run schedules; lag can be hours to days |

---

## 9. Contesting a Signal

Any entity or person that appears in a signal can:

1. **Review evidence** — `GET /signal/{id}/provenance` shows every raw record that contributed.
2. **Check the methodology** — This document and the open-source code describe all detection logic.
3. **File a contestation** — `POST /contestation` allows formal registration of a dispute.
4. **Audit the code** — All typology logic is in `shared/typologies/` (AGPL-3.0 license).

A contestation does not constitute a legal proceeding. Legal disputes follow proper judicial or administrative channels.
