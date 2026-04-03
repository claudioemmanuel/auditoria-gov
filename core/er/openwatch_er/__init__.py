from openwatch_er.normalize import normalize_entity_for_matching
from openwatch_er.matching import deterministic_match, probabilistic_match
from openwatch_er.clustering import cluster_entities
from openwatch_er.edges import build_structural_edges
from openwatch_er.confidence import (
    compute_pair_confidence,
    compute_cluster_confidence,
    EvidenceType,
    MERGE_THRESHOLD,
)

__all__ = [
    "normalize_entity_for_matching",
    "deterministic_match",
    "probabilistic_match",
    "cluster_entities",
    "build_structural_edges",
    "compute_pair_confidence",
    "compute_cluster_confidence",
    "EvidenceType",
    "MERGE_THRESHOLD",
]
