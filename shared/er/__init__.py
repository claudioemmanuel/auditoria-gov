from shared.er.normalize import normalize_entity_for_matching
from shared.er.matching import deterministic_match, probabilistic_match
from shared.er.clustering import cluster_entities
from shared.er.edges import build_structural_edges
from shared.er.confidence import (
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
