"""Tests for _collect_cluster_evidence — pure unit tests, no DB required."""
import uuid

import pytest

from openwatch_pipelines.er_tasks import _collect_cluster_evidence
from openwatch_er.matching import MatchResult
from openwatch_er.clustering import ClusterResult


def _entity(
    entity_id=None,
    identifiers=None,
    attrs=None,
):
    return {
        "id": entity_id or uuid.uuid4(),
        "identifiers": identifiers or {},
        "attrs": attrs or {},
    }


def _match(ea_id, eb_id, score=1.0, match_type="deterministic", reason="CNPJ match"):
    return MatchResult(
        entity_a_id=ea_id,
        entity_b_id=eb_id,
        match_type=match_type,
        score=score,
        reason=reason,
    )


def _cluster(entity_ids):
    ids = list(entity_ids)
    return ClusterResult(cluster_id=ids[0], entity_ids=ids, match_chain=[])


# ── Zero-result: single-entity cluster produces no evidence ──────────────────

def test_single_entity_cluster_produces_no_evidence():
    eid = uuid.uuid4()
    cluster = _cluster([eid])
    entity_lookup = {eid: _entity(entity_id=eid)}

    pair_evidence, entity_confidence = _collect_cluster_evidence([], [cluster], entity_lookup)

    assert pair_evidence == []
    assert entity_confidence == {}


# ── Positive: CNPJ exact match → evidence score 100, cluster_confidence 100 ──

def test_cnpj_exact_match_writes_100_confidence():
    ea_id, eb_id = uuid.uuid4(), uuid.uuid4()
    cnpj = "12345678000100"
    ea = _entity(entity_id=ea_id, identifiers={"cnpj": cnpj})
    eb = _entity(entity_id=eb_id, identifiers={"cnpj": cnpj})
    match = _match(ea_id, eb_id, score=1.0, match_type="deterministic", reason="CNPJ match")
    cluster = _cluster([ea_id, eb_id])
    entity_lookup = {ea_id: ea, eb_id: eb}

    pair_evidence, entity_confidence = _collect_cluster_evidence(
        [match], [cluster], entity_lookup
    )

    assert len(pair_evidence) == 1
    ev = pair_evidence[0]
    assert ev["confidence_score"] == 100
    assert ev["evidence_type"] == "cnpj_exact"
    assert ev["entity_a_id"] == ea_id
    assert ev["entity_b_id"] == eb_id
    assert entity_confidence[ea_id] == 100
    assert entity_confidence[eb_id] == 100


# ── Positive: probabilistic match uses match.score as name_similarity proxy ──

def test_probabilistic_name_match_writes_evidence():
    ea_id, eb_id = uuid.uuid4(), uuid.uuid4()
    ea = _entity(entity_id=ea_id, identifiers={}, attrs={"municipio": "CURITIBA"})
    eb = _entity(entity_id=eb_id, identifiers={}, attrs={"municipio": "CURITIBA"})
    match = _match(ea_id, eb_id, score=0.90, match_type="probabilistic", reason="Name similarity: 0.90")
    cluster = _cluster([ea_id, eb_id])
    entity_lookup = {ea_id: ea, eb_id: eb}

    pair_evidence, entity_confidence = _collect_cluster_evidence(
        [match], [cluster], entity_lookup
    )

    assert len(pair_evidence) == 1
    ev = pair_evidence[0]
    assert ev["evidence_type"] == "name_municipality"
    assert ev["confidence_score"] == 85
    assert entity_confidence[ea_id] == 85


# ── Positive: cluster with 3 entities; weakest-link cluster_confidence ────────

def test_cluster_confidence_is_minimum_of_pair_scores():
    # Entity A (CNPJ exact with B) and B (probabilistic name-only with C)
    ea_id, eb_id, ec_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    cnpj = "99887766000100"
    ea = _entity(entity_id=ea_id, identifiers={"cnpj": cnpj})
    eb = _entity(entity_id=eb_id, identifiers={"cnpj": cnpj})
    ec = _entity(entity_id=ec_id, identifiers={}, attrs={})

    match_ab = _match(ea_id, eb_id, score=1.0, match_type="deterministic")
    # score=0.78 → NAME_FUZZY (55) — same_municipality=False, no co-participation
    match_bc = _match(eb_id, ec_id, score=0.78, match_type="probabilistic", reason="Name similarity: 0.78")

    cluster = _cluster([ea_id, eb_id, ec_id])
    entity_lookup = {ea_id: ea, eb_id: eb, ec_id: ec}

    pair_evidence, entity_confidence = _collect_cluster_evidence(
        [match_ab, match_bc], [cluster], entity_lookup
    )

    scores = {ev["confidence_score"] for ev in pair_evidence}
    assert 100 in scores  # CNPJ exact
    assert 55 in scores   # NAME_FUZZY
    # Cluster confidence = min(100, 55) = 55
    assert entity_confidence[ea_id] == 55
    assert entity_confidence[eb_id] == 55
    assert entity_confidence[ec_id] == 55


# ── Edge: match not in cluster → ignored ─────────────────────────────────────

def test_match_outside_cluster_is_ignored():
    ea_id, eb_id, unrelated_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    ea = _entity(entity_id=ea_id, identifiers={"cnpj": "11111111000100"})
    eb = _entity(entity_id=eb_id, identifiers={"cnpj": "11111111000100"})
    unrelated = _entity(entity_id=unrelated_id, identifiers={"cnpj": "22222222000200"})

    match_in_cluster = _match(ea_id, eb_id, score=1.0)
    match_outside = _match(ea_id, unrelated_id, score=1.0)

    cluster = _cluster([ea_id, eb_id])
    entity_lookup = {ea_id: ea, eb_id: eb, unrelated_id: unrelated}

    pair_evidence, entity_confidence = _collect_cluster_evidence(
        [match_in_cluster, match_outside], [cluster], entity_lookup
    )

    assert len(pair_evidence) == 1
    assert pair_evidence[0]["entity_b_id"] == eb_id
    assert unrelated_id not in entity_confidence


# ── Edge: match with entity missing from lookup → skipped safely ──────────────

def test_missing_entity_in_lookup_does_not_crash():
    ea_id, eb_id = uuid.uuid4(), uuid.uuid4()
    ea = _entity(entity_id=ea_id, identifiers={"cnpj": "55555555000100"})
    # eb NOT in lookup
    match = _match(ea_id, eb_id, score=1.0)
    cluster = _cluster([ea_id, eb_id])
    entity_lookup = {ea_id: ea}  # eb missing

    pair_evidence, entity_confidence = _collect_cluster_evidence(
        [match], [cluster], entity_lookup
    )

    assert pair_evidence == []
    assert entity_confidence == {}
