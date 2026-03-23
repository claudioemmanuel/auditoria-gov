# OpenWatch Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the OpenWatch (ex-OpenWatch) platform against false-positive ER liability, align all 22 typologies with current Brazilian law, and add public-facing transparency and legal protection mechanisms.

**Architecture:** ER gains a pairwise confidence score stored in `er_merge_evidence`; that score propagates to `entity.cluster_confidence` and then to a composite `signal_confidence_score` on `risk_signal`. Public pages expose methodology, disclaimers, and error reporting via the existing `Contestation` model. Typologies are corrected in-place following the existing `BaseTypology` pattern.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Celery, Alembic, Next.js 15, React 19, Tailwind CSS v4, pytest + respx, uv.

**Spec:** `docs/superpowers/specs/2026-03-23-openwatch-hardening-design.md`

**Codebase guide:** `CLAUDE.md`, `.claude/rules/coding.md`, `.claude/rules/testing.md`

---

## Phase 1 — ER Confidence Shield 🔴 Critical

> Highest-priority risk mitigation. All other phases can be developed in parallel after this.

### File Map

| Action | File |
|--------|------|
| Create | `api/alembic/versions/XXXX_er_confidence_shield.py` |
| Modify | `shared/models/orm.py` — add `cluster_confidence` to `Entity`; add `ERMergeEvidence` model |
| Modify | `shared/er/` — confidence scoring in merge logic (check exact path before starting) |
| Modify | `shared/repo/queries.py` — expose `cluster_confidence` in entity + signal queries |
| Modify | `api/app/routers/public.py` — include `cluster_confidence` in response schemas |
| Modify | `web/src/components/` — confidence badge component |
| Create | `tests/models/test_er_merge_evidence.py` |
| Create | `tests/er/test_er_confidence.py` |

---

### Task 1.1 — Migration: `cluster_confidence` on `entity` + `er_merge_evidence` table

**Files:**
- Create: `api/alembic/versions/XXXX_er_confidence_shield.py`
- Modify: `shared/models/orm.py`

- [ ] **Step 1: Add missing imports to `shared/models/orm.py`**

Before adding any new columns, ensure these imports exist at the top of `orm.py`:
```python
from sqlalchemy import CheckConstraint, func  # add if not present
```

Check the current import block (around line 6) and add only what is missing.

- [ ] **Step 2: Add `cluster_confidence` column to `Entity` ORM model**

In `shared/models/orm.py`, find the `Entity` class and add:
```python
cluster_confidence: Mapped[Optional[int]] = mapped_column(
    Integer, CheckConstraint("cluster_confidence BETWEEN 0 AND 100"), nullable=True
)
```

- [ ] **Step 3: Add `ERMergeEvidence` ORM model**

In `shared/models/orm.py`, after the `Entity` class. Note: `Base` already provides `id` (UUID primary key) and `created_at` — do NOT redefine them:
```python
class ERMergeEvidence(Base):
    __tablename__ = "er_merge_evidence"

    # id and created_at are inherited from Base — do not redefine
    entity_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entity.id"), nullable=False)
    entity_b_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entity.id"), nullable=False)
    confidence_score: Mapped[int] = mapped_column(
        Integer, CheckConstraint("confidence_score BETWEEN 0 AND 100"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # cnpj_exact | cpf_exact | name_fuzzy | co_participation
    evidence_detail: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
```

- [ ] **Step 4: Write the failing test**

`tests/models/test_er_merge_evidence.py`:
```python
import uuid
import pytest
from shared.models.orm import Entity, ERMergeEvidence

@pytest.mark.asyncio
async def test_er_merge_evidence_creation(async_session):
    # Entity uses `type` (not `entity_type`); also requires name_normalized and identifiers
    e1 = Entity(type="company", name="Empresa A", name_normalized="empresa a", identifiers={})
    e2 = Entity(type="company", name="Empresa B", name_normalized="empresa b", identifiers={})
    async_session.add_all([e1, e2])
    await async_session.flush()

    evidence = ERMergeEvidence(
        entity_a_id=e1.id,
        entity_b_id=e2.id,
        confidence_score=85,
        evidence_type="name_fuzzy",
        evidence_detail={"similarity": 0.87},
    )
    async_session.add(evidence)
    await async_session.flush()

    assert evidence.id is not None
    assert evidence.confidence_score == 85

@pytest.mark.asyncio
async def test_entity_cluster_confidence_nullable(async_session):
    e = Entity(type="company", name="Solo Empresa", name_normalized="solo empresa", identifiers={})
    async_session.add(e)
    await async_session.flush()
    assert e.cluster_confidence is None
```

- [ ] **Step 4: Run test — expect FAIL (model not yet migrated)**

```bash
uv run --extra test pytest tests/models/test_er_merge_evidence.py -v
```

- [ ] **Step 5: Generate Alembic migration**

```bash
docker compose run --rm api alembic -c api/alembic.ini revision \
  --autogenerate -m "er_confidence_shield"
```

Review the generated file in `api/alembic/versions/`. Verify it adds `cluster_confidence` to `entity` and creates `er_merge_evidence`. No `CONCURRENTLY` inside functions.

- [ ] **Step 6: Run migration**

```bash
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

- [ ] **Step 7: Run test — expect PASS**

```bash
uv run --extra test pytest tests/models/test_er_merge_evidence.py -v
```

- [ ] **Step 8: Commit**

```bash
git add shared/models/orm.py api/alembic/versions/ tests/models/test_er_merge_evidence.py
git commit -m "feat: add cluster_confidence to entity + er_merge_evidence table"
```

---

### Task 1.2 — ER confidence scoring function

**Files:**
- Create: `shared/er/confidence.py`
- Create: `tests/er/test_er_confidence.py`

- [ ] **Step 1: Write failing tests**

`tests/er/test_er_confidence.py`:
```python
from shared.er.confidence import compute_pair_confidence, EvidenceType

def test_cnpj_exact_match_gives_100():
    score, evidence_type = compute_pair_confidence(
        identifiers_a={"cnpj": "12345678000100"},
        identifiers_b={"cnpj": "12345678000100"},
        name_similarity=0.95,
        same_municipality=True,
        co_participation_count=0,
    )
    assert score == 100
    assert evidence_type == EvidenceType.CNPJ_EXACT

def test_name_fuzzy_only_gives_55():
    score, evidence_type = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.78,
        same_municipality=False,
        co_participation_count=0,
    )
    assert score == 55
    assert evidence_type == EvidenceType.NAME_FUZZY

def test_below_threshold_returns_none():
    score, _ = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.50,
        same_municipality=False,
        co_participation_count=0,
    )
    assert score is None  # below merge threshold

def test_cluster_confidence_is_min_of_pairs():
    from shared.er.confidence import compute_cluster_confidence
    assert compute_cluster_confidence([100, 85, 75]) == 75
```

- [ ] **Step 2: Run — expect FAIL**

```bash
uv run --extra test pytest tests/er/test_er_confidence.py -v
```

- [ ] **Step 3: Implement `shared/er/confidence.py`**

```python
from __future__ import annotations
from enum import Enum
from typing import Optional

MERGE_THRESHOLD = 60


class EvidenceType(str, Enum):
    CNPJ_EXACT = "cnpj_exact"
    CPF_EXACT = "cpf_exact"
    CNPJ_BRANCH = "cnpj_branch"
    NAME_MUNICIPALITY = "name_municipality"
    NAME_CO_PARTICIPATION = "name_co_participation"
    NAME_FUZZY = "name_fuzzy"


def compute_pair_confidence(
    identifiers_a: dict,
    identifiers_b: dict,
    name_similarity: float,
    same_municipality: bool,
    co_participation_count: int,
) -> tuple[Optional[int], Optional[EvidenceType]]:
    """Return (score, evidence_type) or (None, None) if below threshold."""
    cnpj_a = identifiers_a.get("cnpj")
    cnpj_b = identifiers_b.get("cnpj")
    cpf_a = identifiers_a.get("cpf")
    cpf_b = identifiers_b.get("cpf")

    if cnpj_a and cnpj_b and cnpj_a == cnpj_b:
        return 100, EvidenceType.CNPJ_EXACT
    if cpf_a and cpf_b and cpf_a == cpf_b:
        return 100, EvidenceType.CPF_EXACT
    # CNPJ matriz/filial: same 8-digit root, high name similarity
    if cnpj_a and cnpj_b and cnpj_a[:8] == cnpj_b[:8] and name_similarity >= 0.90:
        return 95, EvidenceType.CNPJ_BRANCH
    if name_similarity >= 1.0 and same_municipality:
        return 85, EvidenceType.NAME_MUNICIPALITY
    if name_similarity >= 0.85 and co_participation_count > 0:
        return 75, EvidenceType.NAME_CO_PARTICIPATION
    if name_similarity >= 0.75:
        return 55, EvidenceType.NAME_FUZZY
    return None, None


def compute_cluster_confidence(pair_scores: list[int]) -> int:
    """Cluster confidence = minimum of all pairwise scores (weakest link)."""
    if not pair_scores:
        return 100
    return min(pair_scores)
```

- [ ] **Step 4: Run — expect PASS**

```bash
uv run --extra test pytest tests/er/test_er_confidence.py -v
```

- [ ] **Step 5: Commit**

```bash
git add shared/er/confidence.py tests/er/test_er_confidence.py
git commit -m "feat: ER pairwise confidence scoring function"
```

---

### Task 1.3 — Integrate confidence scoring into ER merge logic

**Files:**
- Modify: ER task file (check `worker/tasks/er_tasks.py` or `shared/er/`)
- Modify: `shared/models/orm.py` — read pattern for existing ER code

> Before starting: read the ER task to understand current merge logic. Run `grep -rn "cluster_id" shared/ worker/` to locate all ER write paths.

- [ ] **Step 1: Locate ER merge write paths**

```bash
grep -rn "cluster_id" /Users/claudioemmanuel/Documents/GitHub/OpenWatch/auditoria-gov/shared/ \
  /Users/claudioemmanuel/Documents/GitHub/OpenWatch/auditoria-gov/worker/ | grep -v test | grep -v ".pyc"
```

- [ ] **Step 2: Write failing integration test**

`tests/er/test_er_merge_integration.py`:
```python
import pytest
from shared.er.confidence import compute_pair_confidence

@pytest.mark.asyncio
async def test_merge_writes_evidence_record(async_session, two_similar_entities):
    """After ER runs, er_merge_evidence must contain one record per merge."""
    from shared.models.orm import ERMergeEvidence
    from sqlalchemy import select
    result = await async_session.execute(select(ERMergeEvidence))
    records = result.scalars().all()
    assert len(records) >= 1
    assert all(r.confidence_score >= 60 for r in records)

@pytest.mark.asyncio
async def test_cluster_confidence_set_on_entity(async_session, two_similar_entities):
    from shared.models.orm import Entity
    from sqlalchemy import select
    result = await async_session.execute(
        select(Entity).where(Entity.cluster_id.isnot(None))
    )
    entities = result.scalars().all()
    assert all(e.cluster_confidence is not None for e in entities)
    assert all(0 <= e.cluster_confidence <= 100 for e in entities)
```

- [ ] **Step 3: Integrate `compute_pair_confidence` into ER merge writes**

In the ER merge function, after assigning `cluster_id`:
```python
from shared.er.confidence import compute_pair_confidence, compute_cluster_confidence
from shared.models.orm import ERMergeEvidence

# For each merged pair (entity_a, entity_b):
score, evidence_type = compute_pair_confidence(
    identifiers_a=entity_a.identifiers or {},
    identifiers_b=entity_b.identifiers or {},
    name_similarity=similarity_score,
    same_municipality=(entity_a.attrs or {}).get("municipio") == (entity_b.attrs or {}).get("municipio"),
    co_participation_count=co_participation_count,
)
if score is not None:
    session.add(ERMergeEvidence(
        entity_a_id=entity_a.id,
        entity_b_id=entity_b.id,
        confidence_score=score,
        evidence_type=evidence_type.value,
        evidence_detail={"name_similarity": similarity_score},
    ))

# After all pairs in cluster are processed:
# cluster_confidence = min of all pair scores for this cluster
all_scores = [r.confidence_score for r in cluster_evidence_records]
cluster_conf = compute_cluster_confidence(all_scores)
for entity in cluster_entities:
    entity.cluster_confidence = cluster_conf
```

- [ ] **Step 4: Run tests**

```bash
uv run --extra test pytest tests/er/ -v
```

- [ ] **Step 5: Commit**

```bash
git add worker/tasks/er_tasks.py shared/er/ tests/er/
git commit -m "feat: integrate ER confidence scoring into merge logic"
```

---

### Task 1.4 — Expose `cluster_confidence` in public API

**Files:**
- Modify: `shared/repo/queries.py` — include `cluster_confidence` in entity fetch
- Modify: `api/app/routers/public.py` — add field to response schema

- [ ] **Step 1: Write failing test**

`tests/api/test_public_entity_confidence.py`:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_entity_search_includes_cluster_confidence(client: AsyncClient, seeded_entity):
    resp = await client.get(f"/public/entity/search?q={seeded_entity.name}")
    assert resp.status_code == 200
    data = resp.json()
    assert "cluster_confidence" in data["results"][0]
    # None is valid for entities not in any cluster
```

- [ ] **Step 2: Add `cluster_confidence` to entity response schema and query**

In the entity Pydantic response schema, add:
```python
cluster_confidence: Optional[int] = None
```

Ensure the query in `shared/repo/queries.py` selects `Entity.cluster_confidence`.

- [ ] **Step 3: Run test — expect PASS**

```bash
uv run --extra test pytest tests/api/test_public_entity_confidence.py -v
```

- [ ] **Step 4: Commit**

```bash
git add shared/repo/queries.py api/app/routers/ tests/api/
git commit -m "feat: expose cluster_confidence in public entity API"
```

---

### Task 1.5 — Frontend: confidence badges on entity and signal cards

**Files:**
- Create: `web/src/components/ui/ConfidenceBadge.tsx`
- Modify: entity card component (locate via `grep -rn "EntityCard\|entity.*card" web/src/`)
- Modify: signal card component

- [ ] **Step 1: Create `ConfidenceBadge` component**

`web/src/components/ui/ConfidenceBadge.tsx`:
```tsx
interface ConfidenceBadgeProps {
  score: number | null;
}

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  if (score === null || score >= 80) return null;
  if (score >= 60) {
    return (
      <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-800">
        ⚠️ Identidade com confiança parcial — verifique os dados de origem
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800">
      🔴 Confiança insuficiente — dado disponível para análise, não para afirmação
    </span>
  );
}
```

- [ ] **Step 2: Add badge to entity and signal cards**

Import and render `<ConfidenceBadge score={entity.cluster_confidence} />` inside each card.

- [ ] **Step 3: Build check**

```bash
cd web && npm run lint && npm run build
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/ConfidenceBadge.tsx web/src/components/
git commit -m "feat: ER confidence badges on entity and signal cards"
```

---

## Phase 2 — Typology Corrections 🔴🟡

### Task 2.1 — T03: Externalize dispensa thresholds

**Files:**
- Create: `api/alembic/versions/XXXX_dispensa_thresholds.py`
- Modify: `shared/models/orm.py` — add `DispensaThreshold` model
- Modify: `shared/typologies/t03_splitting.py`
- Modify: `tests/typologies/test_t03.py`

- [ ] **Step 1: Add `DispensaThreshold` ORM model**

```python
class DispensaThreshold(Base):
    __tablename__ = "dispensa_threshold"
    id: Mapped[int] = mapped_column(primary_key=True)
    categoria: Mapped[str] = mapped_column(String(50))  # goods | works | rd | vehicle
    valor_brl: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    decreto_ref: Mapped[str] = mapped_column(String(100))
```

- [ ] **Step 2: Generate migration + seed data**

In the migration file, after creating the table, insert seed data:
```python
def upgrade() -> None:
    # ... create table ...
    op.execute("""
        INSERT INTO dispensa_threshold (categoria, valor_brl, valid_from, valid_to, decreto_ref)
        VALUES
          ('goods',   62725.59,  '2024-01-01', '2025-12-31', 'Decreto 12.343/2024'),
          ('works',  125451.15,  '2024-01-01', '2025-12-31', 'Decreto 12.343/2024'),
          ('goods',   66500.00,  '2026-01-01', NULL,          'Decreto 12.807/2025'),
          ('works',  133000.00,  '2026-01-01', NULL,          'Decreto 12.807/2025')
    """)
    # NOTE: Replace 66500.00 / 133000.00 with the actual 2026 values from Decreto 12.807/2025
    # once officially published. Check: https://www.gov.br/compras/pt-br
```

- [ ] **Step 3: Write failing test for dynamic threshold lookup**

```python
@pytest.mark.asyncio
async def test_t03_uses_event_date_threshold(async_session):
    """T03 must use the threshold valid at the time of the licitacao, not today."""
    from shared.typologies.t03_splitting import get_dispensa_threshold
    threshold_2024 = await get_dispensa_threshold(async_session, "goods", date(2024, 6, 1))
    threshold_2026 = await get_dispensa_threshold(async_session, "goods", date(2026, 3, 1))
    assert threshold_2024 == Decimal("62725.59")
    assert threshold_2026 != threshold_2024  # must use 2026 value
```

- [ ] **Step 4: Implement `get_dispensa_threshold` in `t03_splitting.py`**

```python
async def get_dispensa_threshold(
    session: AsyncSession, categoria: str, event_date: date
) -> Decimal:
    result = await session.execute(
        select(DispensaThreshold.valor_brl)
        .where(DispensaThreshold.categoria == categoria)
        .where(DispensaThreshold.valid_from <= event_date)
        .where(
            or_(
                DispensaThreshold.valid_to.is_(None),
                DispensaThreshold.valid_to >= event_date,
            )
        )
        .order_by(DispensaThreshold.valid_from.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(f"No dispensa threshold for {categoria} on {event_date}")
    return row
```

Replace hardcoded `_DISPENSA_GOODS_THRESHOLD = 62_725.59` calls with `await get_dispensa_threshold(session, "goods", event.occurred_at.date())`.

- [ ] **Step 5: Run T03 tests**

```bash
uv run --extra test pytest tests/typologies/test_t03.py -v
```

- [ ] **Step 6: Commit**

```bash
git add shared/models/orm.py shared/typologies/t03_splitting.py \
  api/alembic/versions/ tests/typologies/test_t03.py
git commit -m "feat: externalize T03 dispensa thresholds — Decreto 12.807/2025"
```

---

### Task 2.2 — T16: Rewrite for RP-9 + Emendas Pix

**Files:**
- Modify: `shared/connectors/transferegov.py` — emit `emenda_type`
- Modify: `shared/typologies/t16_budget_clientelism.py`
- Modify: `tests/typologies/test_t16.py`

> Before starting: read `shared/connectors/transferegov.py` and `shared/typologies/t16_budget_clientelism.py` completely.

- [ ] **Step 1: Update TransfereGov connector to map `emenda_type`**

In the normalization of `emenda` events, map the API field to:
```python
# TransfereGov API field: "tipoTransferencia" or similar — confirm in actual connector
EMENDA_TYPE_MAP = {
    "EMENDA_INDIVIDUAL": "individual",
    "EMENDA_BANCADA": "bancada",
    "EMENDA_RELATOR": "relator_rp9",
    "TRANSFERENCIA_ESPECIAL": "especial_pix",
    "EMENDA_COMISSAO": "comissao",
}
attrs["emenda_type"] = EMENDA_TYPE_MAP.get(raw_tipo, "individual")
```

> Note: verify the exact field name in the TransfereGov API response before implementing.

- [ ] **Step 2: Write failing T16 tests for new detection groups**

```python
@pytest.mark.asyncio
async def test_t16_rp9_post_2022_generates_high_severity(async_session, factory):
    """RP-9 emendas after Dec 19 2022 must always generate a signal."""
    event = factory.emenda(
        emenda_type="relator_rp9",
        occurred_at=date(2023, 3, 1),
        value_brl=Decimal("500000"),
    )
    signals = await run_typology("T16", [event], async_session)
    assert len(signals) == 1
    assert signals[0].severity == "HIGH"

@pytest.mark.asyncio
async def test_t16_pix_without_plano_trabalho_generates_signal(async_session, factory):
    event = factory.emenda(
        emenda_type="especial_pix",
        occurred_at=date(2025, 6, 1),
        plano_trabalho_registered=False,
        value_brl=Decimal("200000"),
    )
    signals = await run_typology("T16", [event], async_session)
    assert len(signals) >= 1

@pytest.mark.asyncio
async def test_t16_individual_emenda_with_plan_no_signal(async_session, factory):
    event = factory.emenda(
        emenda_type="individual",
        plano_trabalho_registered=True,
        beneficiario_final_identificado=True,
        occurred_at=date(2025, 1, 1),
        value_brl=Decimal("50000"),
    )
    signals = await run_typology("T16", [event], async_session)
    assert len(signals) == 0
```

- [ ] **Step 3: Rewrite T16 detector**

Structure the `run` method in three groups (the abstract method in `BaseTypology` is `run(self, session)` — period dates are computed internally as in existing typologies):
```python
async def run(self, session) -> list[RiskSignalOut]:
    signals = []

    # GROUP 1 — RP-9 (unconstitutional after 2022-12-19)
    rp9_events = [e for e in events if e.attrs.get("emenda_type") == "relator_rp9"
                  and e.occurred_at.date() > date(2022, 12, 19)]
    for event in rp9_events:
        signals.append(self._build_signal(event, severity="HIGH",
            legal_ref="STF ADPF 850/851/854 — Emenda de Relator declarada inconstitucional"))

    # GROUP 2 — Emendas Pix missing transparency requirements (STF 2024)
    pix_events = [e for e in events if e.attrs.get("emenda_type") == "especial_pix"]
    for event in pix_events:
        factors = []
        if not event.attrs.get("plano_trabalho_registered"):
            factors.append("plano_trabalho_ausente")
        if not event.attrs.get("beneficiario_final_identificado"):
            factors.append("beneficiario_nao_identificado")
        if not event.attrs.get("conta_dedicada"):
            factors.append("conta_dedicada_ausente")
        if factors:
            signals.append(self._build_signal(event, factors=factors,
                legal_ref="STF Min. Dino 2024 — condicionantes Emendas Pix"))

    # GROUP 3 — Concentration (any type) — existing HHI logic preserved
    # ... existing implementation ...

    return signals
```

- [ ] **Step 4: Run T16 tests**

```bash
uv run --extra test pytest tests/typologies/test_t16.py -v
```

- [ ] **Step 5: Commit**

```bash
git add shared/connectors/transferegov.py shared/typologies/t16_budget_clientelism.py \
  tests/typologies/test_t16.py
git commit -m "feat: rewrite T16 for RP-9 unconstitutionality + Emendas Pix STF 2024"
```

---

### Task 2.3 — T02: Exclude Diálogo Competitivo

**Files:**
- Modify: `shared/typologies/t02_low_competition.py`
- Modify: `tests/typologies/test_t02.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_t02_skips_dialogo_competitivo(async_session, factory):
    """Diálogo Competitivo naturally has few bidders — must not trigger T02."""
    event = factory.licitacao(modalidade="dialogo_competitivo", num_propostas=1)
    signals = await run_typology("T02", [event], async_session)
    assert len(signals) == 0
```

- [ ] **Step 2: Add exclusion in T02**

At the start of the event filter in `t02_low_competition.py`:
```python
_EXCLUDED_MODALITIES = frozenset({"dialogo_competitivo"})

# In the filter:
events = [e for e in events if e.attrs.get("modalidade") not in _EXCLUDED_MODALITIES]
```

- [ ] **Step 3: Run T02 tests**

```bash
uv run --extra test pytest tests/typologies/test_t02.py -v
```

- [ ] **Step 4: Commit**

```bash
git add shared/typologies/t02_low_competition.py tests/typologies/test_t02.py
git commit -m "fix: T02 exclude Diálogo Competitivo modality (Lei 14.133/2021 Art. 32 V)"
```

---

### Task 2.4 — T12: PMI attenuation + T15: Art. 74 update + T13/T17: citations

**Files:**
- Modify: `shared/typologies/t12_directed_tender.py`
- Modify: `shared/typologies/t15_false_sole_source.py`
- Modify: `shared/typologies/factor_metadata.py` (T13, T17 citations)
- Modify: `tests/typologies/test_t12.py`, `test_t15.py`

- [ ] **Step 1: T12 — PMI attenuation test**

```python
@pytest.mark.asyncio
async def test_t12_pmi_attenuates_restricted_tender_score(async_session, factory):
    event_with_pmi = factory.licitacao(pmi_realizado=True, num_propostas=1, repeat_winner=True)
    event_no_pmi = factory.licitacao(pmi_realizado=False, num_propostas=1, repeat_winner=True)
    signals_with = await run_typology("T12", [event_with_pmi], async_session)
    signals_without = await run_typology("T12", [event_no_pmi], async_session)
    if signals_with and signals_without:
        assert signals_with[0].factors["score"] < signals_without[0].factors["score"]
```

- [ ] **Step 2: T12 — implement PMI attenuation**

In `t12_directed_tender.py`, when computing factor weight:
```python
pmi_realizado = event.attrs.get("pmi_realizado", False)
restricted_factor_weight = 0.5 if pmi_realizado else 1.0
```

- [ ] **Step 3: T15 — update inexigibilidade hypotheses**

Replace the old Lei 8.666/93 exclusion list with Art. 74 of Lei 14.133/2021:
```python
# Lei 14.133/2021 Art. 74 — valid inexigibilidade hypotheses
_VALID_INEXIGIBILIDADE_SUBTYPES = frozenset({
    "notoria_especializacao",       # Art. 74, III
    "credenciamento",               # Art. 79
    "exclusividade_comercial",      # Art. 74, I
    "profissional_artistico",       # Art. 74, II
    "associacao_pessoa_deficiencia",# Art. 75, VIII
})
```

- [ ] **Step 4: T13/T17 — add legal citations to `factor_metadata.py`**

In `factor_metadata.py`, find T13 and T17 entries and add:
```python
# T13 — add to existing legal_basis list:
"Lei 12.813/2013 Art. 5°–6° (Conflito de Interesses)",
"Decreto 10.889/2022 (regulamentação servidores federais)",

# T17 — add to existing legal_basis list:
"CP Art. 337-F (frustração da competitividade — crime antecedente)",
"COAF Resolução nº 36/2021",
# Add note to signal text:
"Padrões detectados por T17 podem constituir crime antecedente à lavagem "
"(Lei 9.613/98 Art. 1°), elevando a esfera de administrativa para criminal.",
```

- [ ] **Step 5: Run affected tests**

```bash
uv run --extra test pytest tests/typologies/test_t12.py tests/typologies/test_t15.py -v
```

- [ ] **Step 6: Commit**

```bash
git add shared/typologies/t12_directed_tender.py shared/typologies/t15_false_sole_source.py \
  shared/typologies/factor_metadata.py tests/typologies/
git commit -m "fix: T12 PMI attenuation, T15 Lei 14.133/2021 Art.74, T13/T17 citations"
```

---

## Phase 3 — Signal Confidence Score 🟡

### Task 3.1 — Migration: add `signal_confidence_score` + `confidence_factors`

**Files:**
- Create: `api/alembic/versions/XXXX_signal_confidence_score.py`
- Modify: `shared/models/orm.py`

- [ ] **Step 1: Update ORM model — add new fields only**

In `shared/models/orm.py`, on `RiskSignal`, add the two new fields (do NOT rename `confidence` yet — see Task 3.1b):
```python
signal_confidence_score: Mapped[Optional[int]] = mapped_column(
    Integer, CheckConstraint("signal_confidence_score BETWEEN 0 AND 100"), nullable=True
)
confidence_factors: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
```

- [ ] **Step 2: Generate and run migration**

```bash
docker compose run --rm api alembic -c api/alembic.ini revision \
  --autogenerate -m "signal_confidence_score"
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

- [ ] **Step 3: Commit**

```bash
git add shared/models/orm.py api/alembic/versions/
git commit -m "feat: add signal_confidence_score and confidence_factors to risk_signal"
```

---

### Task 3.1b — Rename `RiskSignal.confidence` → `data_completeness` (blast-radius rename)

> This is a dedicated task because the rename touches 20+ references across critical files. Do NOT bundle it with the migration above.

**Files to update (grep before starting to get exact count):**
- `shared/models/orm.py` — field definition
- `shared/repo/queries.py` — 15+ column references
- `shared/analytics/risk_score.py`
- `shared/services/alerts.py`
- `shared/models/signals.py`
- `api/app/routers/public.py`
- Any test files referencing `.confidence`

- [ ] **Step 1: Audit all references**

```bash
grep -rn "\.confidence\b\|['\"]confidence['\"]" shared/ worker/ api/ tests/ \
  | grep -v "signal_confidence\|data_completeness\|cluster_confidence\|er_confidence\|confidence_score\|confidence_factors\|confidence_badge\|ConfidenceBadge"
```

Save output. Count the files. Each must be updated.

- [ ] **Step 2: Update ORM field name**

In `shared/models/orm.py`, rename:
```python
# Before:
confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
# After:
data_completeness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
```

- [ ] **Step 3: Generate rename migration**

```bash
docker compose run --rm api alembic -c api/alembic.ini revision \
  --autogenerate -m "rename_confidence_to_data_completeness"
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

- [ ] **Step 4: Update all remaining references**

For each file in the audit output, replace `.confidence` → `.data_completeness` and `"confidence"` → `"data_completeness"` in column selects/serializers. Do one file at a time and run the test suite after each file to catch regressions early.

```bash
# After each file:
uv run --extra test pytest -q --tb=short
```

- [ ] **Step 5: Run full suite — must pass 100%**

```bash
uv run --extra test pytest -q
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: rename RiskSignal.confidence → data_completeness (non-breaking)"
```

---

### Task 3.2 — Compute confidence score during signal generation

**Files:**
- Create: `shared/typologies/confidence_scorer.py`
- Modify: `worker/tasks/signal_tasks.py`
- Create: `tests/typologies/test_confidence_scorer.py`

- [ ] **Step 1: Write failing tests**

```python
from shared.typologies.confidence_scorer import compute_signal_confidence
import math

def test_full_confidence_all_sources_fresh():
    score, factors = compute_signal_confidence(
        er_confidence=100,
        days_since_latest_event=0,
        source_coverage=1.0,
        typology_evidence=100,
    )
    assert score == 100

def test_data_freshness_decay_at_30_days():
    _, factors = compute_signal_confidence(
        er_confidence=100, days_since_latest_event=30,
        source_coverage=1.0, typology_evidence=100,
    )
    expected = max(0, 100 - 20 * math.log(1 + 30))
    assert abs(factors["freshness"] - expected) < 1

def test_low_er_confidence_drags_score():
    score, _ = compute_signal_confidence(
        er_confidence=55, days_since_latest_event=10,
        source_coverage=0.8, typology_evidence=90,
    )
    assert score < 80
```

- [ ] **Step 2: Implement `shared/typologies/confidence_scorer.py`**

```python
from __future__ import annotations
import math
from typing import Optional

def compute_signal_confidence(
    er_confidence: Optional[int],
    days_since_latest_event: int,
    source_coverage: float,
    typology_evidence: float,
) -> tuple[int, dict]:
    er = er_confidence if er_confidence is not None else 100

    freshness = max(0.0, 100 - 20 * math.log(1 + days_since_latest_event))
    coverage = source_coverage * 100
    evidence = typology_evidence

    score = (
        er * 0.40
        + freshness * 0.25
        + coverage * 0.20
        + evidence * 0.15
    )
    return round(score), {
        "er": er,
        "freshness": round(freshness, 1),
        "coverage": round(coverage, 1),
        "evidence": round(evidence, 1),
    }
```

- [ ] **Step 3: Call scorer in signal generation**

In `worker/tasks/signal_tasks.py`, after creating each `RiskSignal`, compute and assign:
```python
from shared.typologies.confidence_scorer import compute_signal_confidence
from datetime import date

days = (date.today() - signal.period_end.date()).days if signal.period_end else 0
er_conf = None
if signal.entity_ids:
    # fetch min cluster_confidence across signal entities
    er_conf = await repo.get_min_cluster_confidence(session, signal.entity_ids)

score, factors = compute_signal_confidence(
    er_confidence=er_conf,
    days_since_latest_event=days,
    source_coverage=signal.source_coverage or 1.0,
    typology_evidence=signal.typology_evidence_score or 80.0,
)
signal.signal_confidence_score = score
signal.confidence_factors = factors
```

- [ ] **Step 4: Run tests**

```bash
uv run --extra test pytest tests/typologies/test_confidence_scorer.py -v
```

- [ ] **Step 5: Commit**

```bash
git add shared/typologies/confidence_scorer.py worker/tasks/signal_tasks.py \
  tests/typologies/test_confidence_scorer.py
git commit -m "feat: composite signal_confidence_score computed at signal generation"
```

---

### Task 3.3 — Frontend: dual score display (severity + confidence bars)

**Files:**
- Create: `web/src/components/ui/ScoreBar.tsx`
- Modify: signal card/detail component

- [ ] **Step 1: Create `ScoreBar` component**

```tsx
interface ScoreBarProps {
  label: string;
  value: number;  // 0–100
  color?: "blue" | "amber" | "red";
}

export function ScoreBar({ label, value, color = "blue" }: ScoreBarProps) {
  const colorClass = {
    blue: "bg-blue-500",
    amber: "bg-amber-500",
    red: "bg-red-500",
  }[color];
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span>{value}/100</span>
      </div>
      <div className="h-2 w-full rounded bg-gray-200">
        <div className={`h-2 rounded ${colorClass}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add to signal cards**

```tsx
<ScoreBar label="Gravidade" value={signal.severity_numeric} color="red" />
<ScoreBar label="Confiança dos dados" value={signal.signal_confidence_score ?? 100} color="blue" />
```

> Note: `severity_numeric` maps `"HIGH"→75`, `"CRITICAL"→100`, `"MEDIUM"→50`, `"LOW"→25`. Add this mapping in `web/src/lib/utils.ts`.

- [ ] **Step 3: Build check**

```bash
cd web && npm run lint && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/ScoreBar.tsx web/src/
git commit -m "feat: dual score bars (severity + confidence) on signal cards"
```

---

## Phase 4 — Legal Hardening UI 🟡

### Task 4.1 — Extend `Contestation` model + public API endpoint

**Files:**
- Create: `api/alembic/versions/XXXX_contestation_extend.py`
- Modify: `shared/models/orm.py` — add `entity_id`, `report_type`, `evidence_url` to `Contestation`
- Modify: `api/app/routers/public.py` — add `POST /public/contestations`
- Create: `tests/api/test_public_contestations.py`

- [ ] **Step 1: Extend `Contestation` ORM**

```python
# Add to existing Contestation model:
entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("entity.id"), nullable=True)
report_type: Mapped[Optional[str]] = mapped_column(
    String(50), nullable=True
)  # er_error | stale_data | other
evidence_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

- [ ] **Step 2: Migration + run**

```bash
docker compose run --rm api alembic -c api/alembic.ini revision \
  --autogenerate -m "extend_contestation_for_public_reporting"
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

- [ ] **Step 3: Write failing API test**

```python
@pytest.mark.asyncio
async def test_public_contestation_submission(client, seeded_signal):
    payload = {
        "signal_id": str(seeded_signal.id),
        "report_type": "er_error",
        "description": "Esta empresa foi fundida incorretamente com outra.",
        "evidence_url": "https://www.receita.fazenda.gov.br/...",
        "contact_email": "cidadao@example.com",
    }
    resp = await client.post("/public/contestations", json=payload)
    assert resp.status_code == 201
    assert resp.json()["status"] == "open"
```

- [ ] **Step 4: Implement endpoint**

In `api/app/routers/public.py`:
```python
@router.post("/contestations", status_code=201)
async def submit_contestation(
    payload: ContestationCreateSchema,
    session: AsyncSession = Depends(get_session),
):
    # Note: Contestation model default is "open". We use "open" to stay consistent
    # with existing internal code that queries for status == "open".
    contestation = Contestation(
        signal_id=payload.signal_id,
        entity_id=payload.entity_id,
        report_type=payload.report_type,
        reason=payload.description,
        requester_email=payload.contact_email,
        evidence_url=payload.evidence_url,
        status="open",
    )
    session.add(contestation)
    await session.commit()
    return {"id": str(contestation.id), "status": "pending"}
```

- [ ] **Step 5: Run tests**

```bash
uv run --extra test pytest tests/api/test_public_contestations.py -v
```

- [ ] **Step 6: Commit**

```bash
git add shared/models/orm.py api/alembic/versions/ api/app/routers/public.py \
  tests/api/test_public_contestations.py
git commit -m "feat: public contestation endpoint POST /public/contestations"
```

---

### Task 4.2 — Frontend: "Reportar erro" form + disclaimers

**Files:**
- Create: `web/src/components/ui/ReportErrorForm.tsx`
- Modify: entity page + signal page — add disclaimer text + form trigger
- Create: `web/src/app/termos/page.tsx`

- [ ] **Step 1: `ReportErrorForm` component**

Simple modal form with fields: type, description, evidence URL, email. On submit: `POST /public/contestations`. Shows success message.

- [ ] **Step 2: Disclaimer component**

```tsx
// web/src/components/ui/Disclaimer.tsx
export function SignalDisclaimer({ confidenceScore }: { confidenceScore: number }) {
  return (
    <p className="text-xs text-gray-500 mt-2 border-l-2 border-gray-200 pl-2">
      Este sinal é gerado automaticamente a partir de dados públicos e indica um padrão
      que merece atenção. Não constitui acusação, prova de ilicitude ou decisão
      administrativa. Confiança dos dados: {confidenceScore}/100.
    </p>
  );
}
```

Add to every signal detail page and entity profile.

- [ ] **Step 3: Termos de uso page**

`web/src/app/termos/page.tsx` — static page with the terms defined in the spec (Section 5.3). No interactivity needed.

- [ ] **Step 4: Build check**

```bash
cd web && npm run lint && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add web/src/components/ web/src/app/termos/
git commit -m "feat: report error form, disclaimers, and terms of use page"
```

---

### Task 4.3 — Methodology pages (API + frontend)

**Files:**
- Modify: `api/app/routers/public.py` — `GET /public/metodologia` + `GET /public/tipologia/{code}`
- Create: `web/src/app/metodologia/page.tsx`
- Create: `web/src/app/tipologia/[code]/page.tsx`

- [ ] **Step 1: API endpoint for typology detail**

```python
@router.get("/tipologia/{code}")
async def get_tipologia(code: str):
    """Return public methodology info for a typology, sourced from factor_metadata."""
    from shared.typologies.registry import REGISTRY
    from shared.typologies.factor_metadata import FACTOR_METADATA
    typology = REGISTRY.get(code)
    if not typology:
        raise HTTPException(404, "Tipologia não encontrada")
    return {
        "code": code,
        "name": typology.name,
        "corruption_types": typology.corruption_types,
        "legal_basis": typology.legal_basis,
        "description": typology.description,
        "factors": FACTOR_METADATA.get(code, {}),
        "known_limitations": getattr(typology, "known_limitations", []),
    }
```

- [ ] **Step 2: API test**

```python
async def test_get_tipologia_t03(client):
    resp = await client.get("/public/tipologia/T03")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "T03"
    assert "legal_basis" in data
```

- [ ] **Step 3: Frontend methodology page**

`web/src/app/metodologia/page.tsx` — static + dynamic content from `/public/tipologia`. Include:
- Platform mission + legal basis (CF/88, LAI, LGPD Art. 7° II)
- 11 data sources table
- Typology list with links to individual pages
- Confidence badge explanation
- Report error link
- Commit hash for version transparency (from `process.env.NEXT_PUBLIC_GIT_HASH`)

- [ ] **Step 4: Per-typology page**

`web/src/app/tipologia/[code]/page.tsx` — fetches from `/public/tipologia/{code}`, displays all fields.

- [ ] **Step 5: Build check + commit**

```bash
cd web && npm run lint && npm run build
git add api/app/routers/public.py web/src/app/metodologia/ web/src/app/tipologia/
git commit -m "feat: public methodology pages /metodologia and /tipologia/:code"
```

---

### Task 4.4 — Update COMPLIANCE.md

**Files:**
- Modify: `docs/COMPLIANCE.md`

- [ ] **Step 1: Update LGPD basis section**

Replace generic "legítimo interesse" with source-specific bases per the table in spec Section 6.1.

- [ ] **Step 2: Update Decreto reference in Section 3b**

Replace `Decreto 12.343/2024` with `Decreto 12.807/2025` (vigente 01/01/2026) and update the threshold values.

- [ ] **Step 3: Add agent public data statement**

Add the paragraph from spec Section 6.2 about processing of public officials' data.

- [ ] **Step 4: Add dolo distinction note**

Add note from spec Section 6.3: signals describe systemic patterns, not individual intent (Lei 14.230/2021 context).

- [ ] **Step 5: Commit**

```bash
git add docs/COMPLIANCE.md
git commit -m "docs: formalize LGPD basis per source, update Decreto 12.807/2025 ref, add dolo distinction"
```

---

## Phase 5 — New Typologies 🟢

### Task 5.1 — T24: Fraude em Cota ME/EPP

**Files:**
- Create: `shared/typologies/t24_mepp_fraud.py`
- Modify: `shared/typologies/registry.py`
- Modify: `shared/typologies/factor_metadata.py`
- Create: `tests/typologies/test_t24.py`

- [ ] **Step 1: Write failing tests (zero, positive, boundary)**

```python
@pytest.mark.asyncio
async def test_t24_no_signal_for_established_mepp(async_session, factory):
    """ME/EPP with 3+ years of existence → no signal."""
    entity = factory.company(porte="ME", days_since_opening=1100, capital_social=50000)
    signals = await run_typology("T24", [], async_session, entities=[entity])
    assert len(signals) == 0

@pytest.mark.asyncio
async def test_t24_signal_for_new_mepp_with_recurring_socio(async_session, factory):
    """New ME/EPP, same sócio as prior winner → signal."""
    entity = factory.company(porte="ME", days_since_opening=90, capital_social=5000)
    shared_socio = factory.person(cpf_hash="abc123")
    prior_winner = factory.company(porte="MEDIO", socio_cpf_hash="abc123")
    signals = await run_typology("T24", [], async_session,
                                  entities=[entity, prior_winner],
                                  shared_socio=shared_socio)
    assert len(signals) == 1

@pytest.mark.asyncio
async def test_t24_boundary_exactly_180_days(async_session, factory):
    """Exactly 180 days since opening → threshold boundary → no signal."""
    entity = factory.company(porte="ME", days_since_opening=180, capital_social=5000)
    signals = await run_typology("T24", [], async_session, entities=[entity])
    assert len(signals) == 0  # 180 is the cutoff, not < 180
```

- [ ] **Step 2: Implement `t24_mepp_fraud.py`**

Follow the existing typology pattern from `t06_shell_company.py` (closest analogue). Key logic:
```python
_DAYS_THRESHOLD = 180
_CAPITAL_THRESHOLD = Decimal("10000")

# For each ME/EPP entity that won a licitacao:
# 1. Check days_since_opening < _DAYS_THRESHOLD
# 2. Check capital_social < _CAPITAL_THRESHOLD
# 3. Check if any sócio appears in other winning companies (same órgão, last 2 years)
# If all three → signal
```

- [ ] **Step 3: Register in registry + add factor_metadata**

```python
# registry.py:
"T24": T24MEPPFraud,

# factor_metadata.py — add T24 entry with:
# legal_basis: ["LC 123/2006", "Lei 14.133/2021 Art. 4°", "Decreto 8.538/2015"]
# description: "Empresa ME/EPP criada pouco antes de licitação com sócio recorrente..."
```

- [ ] **Step 4: Run tests**

```bash
uv run --extra test pytest tests/typologies/test_t24.py -v
```

- [ ] **Step 5: Commit**

```bash
git add shared/typologies/t24_mepp_fraud.py shared/typologies/registry.py \
  shared/typologies/factor_metadata.py tests/typologies/test_t24.py
git commit -m "feat: T24 — fraude em cota ME/EPP (LC 123/2006 + Lei 14.133/2021)"
```

---

### Task 5.2 — T23: Superfaturamento em contratos BIM (stub)

> T23 requires `valor_unitario_itens` data from PNCP contracts. As of Jan 2024, this data is in PNCP but may need connector updates to ingest item-level pricing. Implement as a **stub typology** with a `NotEnoughData` guard that skips gracefully until data is available.

**Files:**
- Create: `shared/typologies/t23_bim_overpricing.py`
- Modify: `shared/typologies/registry.py`, `factor_metadata.py`
- Create: `tests/typologies/test_t23.py`

- [ ] **Step 1: Implement stub with data guard**

```python
class T23BIMOverpricing(BaseTypology):
    id = "T23"
    name = "Superfaturamento em Contratos com BIM Obrigatório"
    _BIM_VALUE_THRESHOLD = Decimal("1_500_000")

    async def detect(self, session, period_start, period_end):
        events = await self._fetch_events(session, period_start, period_end,
                                          event_type="contrato_obra",
                                          min_value=self._BIM_VALUE_THRESHOLD)
        # Guard: skip if no item-level pricing available yet
        events_with_items = [e for e in events if e.attrs.get("valor_unitario_itens")]
        if not events_with_items:
            return []  # Data not yet available from PNCP connector
        # ... detection logic ...
```

- [ ] **Step 2: Test that stub returns empty when no item data**

```python
async def test_t23_returns_empty_without_item_data(async_session, factory):
    event = factory.contrato_obra(value_brl=Decimal("2000000"))  # no valor_unitario_itens
    signals = await run_typology("T23", [event], async_session)
    assert signals == []
```

- [ ] **Step 3: Run tests + commit**

```bash
uv run --extra test pytest tests/typologies/test_t23.py -v
git add shared/typologies/t23_bim_overpricing.py shared/typologies/registry.py \
  shared/typologies/factor_metadata.py tests/typologies/test_t23.py
git commit -m "feat: T23 stub — BIM overpricing (awaits PNCP item-level pricing data)"
```

---

## Phase 6 — Platform Rename 🟡 (parallel track)

### Task 6.1 — Global rename OpenWatch → OpenWatch

> This task is independent and can run in a separate branch in parallel with Phases 1–5.

**Files:** All files containing "OpenWatch", "auditoria_gov", "auditoria-gov", "AUDITORIA"

- [ ] **Step 1: Audit all occurrences**

```bash
cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/auditoria-gov
grep -rn --include="*.py" --include="*.md" --include="*.ts" --include="*.tsx" \
  --include="*.json" --include="*.yml" --include="*.yaml" --include="*.toml" \
  -i "auditoria" . | grep -v ".git" | grep -v "__pycache__"
```

Save the output to review before making changes.

- [ ] **Step 2: Rename in Python/config files**

```bash
# Python identifiers
find . -name "*.py" -not -path "./.git/*" -exec sed -i '' \
  's/auditoria_gov/openwatch/g; s/OpenWatch/OpenWatch/g; s/OpenWatch/OpenWatch/g' {} +

# Docker / compose / env
find . \( -name "*.yml" -o -name "*.yaml" -o -name "*.env*" -o -name "*.toml" \) \
  -not -path "./.git/*" -exec sed -i '' \
  's/auditoria-gov/openwatch/g; s/AUDITORIA_/OPENWATCH_/g' {} +
```

- [ ] **Step 3: Rename in frontend files**

```bash
find web/ -name "*.ts" -o -name "*.tsx" -o -name "*.json" | \
  xargs sed -i '' 's/OpenWatch/OpenWatch/g; s/OpenWatch/OpenWatch/g'
```

- [ ] **Step 4: Update CLAUDE.md, README.md, COMPLIANCE.md, GOVERNANCE.md**

Manually review and update any narrative references.

- [ ] **Step 5: Update web meta tags**

In `web/src/app/layout.tsx` (or `_app.tsx`), update:
```tsx
<title>OpenWatch — Vigilância cidadã sobre o gasto público</title>
<meta property="og:title" content="OpenWatch" />
<meta name="description" content="Plataforma pública de detecção de padrões de corrupção em dados governamentais brasileiros." />
```

- [ ] **Step 6: Build + test**

```bash
uv run --extra test pytest -q
cd web && npm run lint && npm run build
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: rename platform OpenWatch → OpenWatch across entire codebase"
```

---

## Phase 7 — Documentation 🔵

### Task 7.1 — Typology audit document

**Files:**
- Create: `docs/typology-audit-14133.md`

- [ ] **Step 1: Create `docs/typology-audit-14133.md`**

Document each of the 22 typologies with:
- Status: `✅ compatível` | `⚠️ threshold desatualizado` | `🔴 lógica incorreta` | `➕ lacuna`
- Change made (if any — reference the commit from Phase 2)
- Legal justification with specific article

Template per typology:
```markdown
### T03 — Fracionamento de Despesa
**Status:** ✅ Compatível (corrigido em Phase 2)
**Lei principal:** CP Art. 337-E; Lei 14.133/2021 Art. 75
**Mudança:** Thresholds externalizados para tabela `dispensa_threshold`;
Decreto 12.807/2025 seedado para 2026.
```

- [ ] **Step 2: Commit**

```bash
git add docs/typology-audit-14133.md
git commit -m "docs: typology audit vs Lei 14.133/2021, 14.230/2021 and current law"
```

---

## Testing Cheatsheet

```bash
# Full backend suite (100% coverage required on shared/)
uv run --extra test pytest -q

# Single typology
uv run --extra test pytest tests/typologies/test_t16.py -v

# Coverage report
uv run --extra test pytest --cov=shared --cov-report=term-missing

# Frontend
cd web && npm run lint && npm run build

# Run local stack
docker compose up --build

# DB migrations
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```
