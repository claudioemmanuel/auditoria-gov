# Output Style: Learning / Teaching

## Tone & Format

- Explain *why* before *how*.
- Use concrete examples from this codebase, not generic examples.
- Break concepts into numbered steps.
- Define domain terms on first use (e.g., "typology — a pattern-based rule for detecting a corruption signal").

## Structure for Explanations

1. **Context** — why this exists in the project
2. **Concept** — the idea in plain language
3. **Example** — a real file/function from the codebase
4. **Common mistakes** — what goes wrong and why
5. **Next step** — what to read or try next

## Domain Vocabulary (AuditorIA Gov)

| Term | Meaning |
|------|---------|
| Typology | A deterministic rule that detects a corruption signal pattern |
| Signal | An instance of a typology firing on real data |
| Entity Resolution (ER) | Cross-source deduplication of companies/people |
| Baseline | Historical price/cost benchmark for anomaly detection |
| Connector | A data source adapter (e.g., PNCP, TransfereGov) |
| Dispensa | Direct procurement without bidding (Brazilian law) |

## When Explaining Code

- Show the call chain from API router → repo query → DB.
- Link to the relevant test file to show expected behavior.
- Point to `docs/ARCHITECTURE.md` for the big picture.
