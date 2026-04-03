import uuid
from dataclasses import dataclass, field

from shared.er.matching import MatchResult


class UnionFind:
    """Union-Find (Disjoint Set Union) for entity clustering."""

    def __init__(self) -> None:
        self.parent: dict[uuid.UUID, uuid.UUID] = {}
        self.rank: dict[uuid.UUID, int] = {}

    def find(self, x: uuid.UUID) -> uuid.UUID:
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: uuid.UUID, y: uuid.UUID) -> uuid.UUID:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return rx
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return rx


@dataclass
class ClusterResult:
    cluster_id: uuid.UUID
    entity_ids: list[uuid.UUID]
    match_chain: list[MatchResult]


def cluster_entities(matches: list[MatchResult]) -> list[ClusterResult]:
    """Build clusters from pairwise match results using Union-Find.

    Non-destructive: stores cluster_id in entity.attrs rather than merging.
    """
    uf = UnionFind()

    for m in matches:
        uf.union(m.entity_a_id, m.entity_b_id)

    # Group by cluster root
    clusters: dict[uuid.UUID, list[uuid.UUID]] = {}
    all_ids = set()
    for m in matches:
        all_ids.add(m.entity_a_id)
        all_ids.add(m.entity_b_id)

    for eid in all_ids:
        root = uf.find(eid)
        clusters.setdefault(root, []).append(eid)

    # Assign cluster IDs and gather match chains
    results = []
    for root, entity_ids in clusters.items():
        cluster_id = root  # Use the root entity as cluster ID
        chain = [
            m
            for m in matches
            if m.entity_a_id in entity_ids or m.entity_b_id in entity_ids
        ]
        results.append(
            ClusterResult(
                cluster_id=cluster_id,
                entity_ids=sorted(set(entity_ids)),
                match_chain=chain,
            )
        )

    return results
