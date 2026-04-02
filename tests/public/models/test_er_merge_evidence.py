import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from openwatch_models.orm import Entity, ERMergeEvidence

@pytest.mark.asyncio
async def test_er_merge_evidence_creation(async_session):
    # Entity uses `type` (not `entity_type`); requires name_normalized and identifiers
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

@pytest.mark.asyncio
async def test_er_merge_evidence_confidence_score_boundary(async_session):
    """Boundary: confidence_score must be between 0 and 100."""
    e1 = Entity(type="company", name="Empresa C", name_normalized="empresa c", identifiers={})
    e2 = Entity(type="company", name="Empresa D", name_normalized="empresa d", identifiers={})
    async_session.add_all([e1, e2])
    await async_session.flush()
    # Valid boundary values
    for score in [0, 60, 100]:
        ev = ERMergeEvidence(
            entity_a_id=e1.id, entity_b_id=e2.id,
            confidence_score=score, evidence_type="cnpj_exact",
        )
        async_session.add(ev)
    await async_session.flush()

@pytest.mark.asyncio
async def test_er_merge_evidence_rejects_invalid_score(async_session):
    e1 = Entity(type="company", name="X", name_normalized="x", identifiers={})
    e2 = Entity(type="company", name="Y", name_normalized="y", identifiers={})
    async_session.add_all([e1, e2])
    await async_session.flush()
    ev = ERMergeEvidence(
        entity_a_id=e1.id, entity_b_id=e2.id,
        confidence_score=101, evidence_type="cnpj_exact",
    )
    async_session.add(ev)
    with pytest.raises(IntegrityError):
        await async_session.flush()
