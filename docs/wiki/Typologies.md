# Typologies

The typology engine runs deterministic detectors registered in `shared/typologies/registry.py`.

| Code | Typology |
|---|---|
| T01 | Supplier concentration |
| T02 | Low competition |
| T03 | Expense splitting |
| T04 | Parliamentary amendment outlier |
| T05 | Price outlier |
| T06 | Shell company proxy |
| T07 | Cartel network |
| T08 | Sanctions mismatch |
| T09 | Ghost payroll proxy |
| T10 | Outsourcing + parallel payroll |

## Detector Quality Expectations

- Numeric factors and transparent thresholds
- Reproducible evidence linked to raw/canonical records
- Test coverage for minimum-detectable scenarios
- Deterministic outputs for the same input data
