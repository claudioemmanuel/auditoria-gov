import uuid

from shared.er.clustering import UnionFind, cluster_entities
from shared.er.matching import MatchResult


def _match(a_id, b_id, score=1.0):
    return MatchResult(
        entity_a_id=a_id,
        entity_b_id=b_id,
        match_type="deterministic",
        score=score,
        reason="test",
    )


class TestUnionFind:
    def test_find_new_element(self):
        uf = UnionFind()
        x = uuid.uuid4()
        assert uf.find(x) == x

    def test_union_same_root(self):
        uf = UnionFind()
        x = uuid.uuid4()
        y = uuid.uuid4()
        root = uf.union(x, y)
        assert uf.find(x) == uf.find(y)
        assert root in (x, y)

    def test_union_transitive(self):
        uf = UnionFind()
        a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        uf.union(a, b)
        uf.union(b, c)
        assert uf.find(a) == uf.find(c)

    def test_separate_components(self):
        uf = UnionFind()
        a, b = uuid.uuid4(), uuid.uuid4()
        c, d = uuid.uuid4(), uuid.uuid4()
        uf.union(a, b)
        uf.union(c, d)
        assert uf.find(a) != uf.find(c)

    def test_union_idempotent(self):
        uf = UnionFind()
        a, b = uuid.uuid4(), uuid.uuid4()
        r1 = uf.union(a, b)
        r2 = uf.union(a, b)
        assert r1 == r2

    def test_path_compression(self):
        uf = UnionFind()
        ids = [uuid.uuid4() for _ in range(5)]
        for i in range(len(ids) - 1):
            uf.union(ids[i], ids[i + 1])
        root = uf.find(ids[-1])
        # After path compression, all point to root
        for uid in ids:
            assert uf.find(uid) == root


class TestClusterEntities:
    def test_single_match_single_cluster(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        matches = [_match(a, b)]
        clusters = cluster_entities(matches)
        assert len(clusters) == 1
        assert set(clusters[0].entity_ids) == {a, b}

    def test_chain_creates_single_cluster(self):
        a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        matches = [_match(a, b), _match(b, c)]
        clusters = cluster_entities(matches)
        assert len(clusters) == 1
        assert set(clusters[0].entity_ids) == {a, b, c}

    def test_separate_clusters(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        c, d = uuid.uuid4(), uuid.uuid4()
        matches = [_match(a, b), _match(c, d)]
        clusters = cluster_entities(matches)
        assert len(clusters) == 2

    def test_empty_matches(self):
        clusters = cluster_entities([])
        assert len(clusters) == 0

    def test_match_chain_preserved(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        m = _match(a, b)
        clusters = cluster_entities([m])
        assert len(clusters[0].match_chain) == 1
        assert clusters[0].match_chain[0] == m

    def test_cluster_id_is_root(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        clusters = cluster_entities([_match(a, b)])
        assert clusters[0].cluster_id in (a, b)


class TestUnionFindRankSwap:
    def test_rank_swap_when_rx_lower(self):
        """Cover line 27: when rx.rank < ry.rank, swap occurs."""
        uf = UnionFind()
        a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        # Union a and b → root gets rank 1
        uf.union(a, b)
        root_ab = uf.find(a)
        assert uf.rank[root_ab] == 1

        # c is new, rank 0 — union(c, root_ab) triggers swap since rank[c]=0 < rank[root]=1
        result = uf.union(c, root_ab)
        assert result == root_ab
        assert uf.find(c) == root_ab
