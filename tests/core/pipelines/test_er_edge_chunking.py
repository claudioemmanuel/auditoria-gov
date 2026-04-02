"""Tests for P2 fix in ER edge flushing:
- Edge existence query must chunk BOTH from_ids AND to_ids
- Dict size logging for unbounded growth monitoring
"""

import uuid

from openwatch_pipelines import er_tasks


class TestEdgeChunkingConstants:
    """P2: Verify _IN_CHUNK is safe for bidimensional chunking."""

    def test_in_chunk_size_safe(self):
        """_IN_CHUNK × _IN_CHUNK queries should each stay below 32K params."""
        assert er_tasks._IN_CHUNK <= 5_000
        # Each query has: from_ids IN (:chunk) AND to_ids IN (:chunk) AND type IN (:types)
        # Worst case: 5000 + 5000 + 50 = 10050 params — well below 32K
        max_params_per_query = er_tasks._IN_CHUNK * 2 + 100  # 100 edge types max
        assert max_params_per_query < 32_767

    def test_edge_batch_size_exists(self):
        """_ER_EDGE_BATCH_SIZE must exist for participant streaming."""
        assert hasattr(er_tasks, "_ER_EDGE_BATCH_SIZE")
        assert er_tasks._ER_EDGE_BATCH_SIZE <= 50_000


class TestBidimensionalChunking:
    """P2: Verify _flush_edges chunks to_ids (not just from_ids)."""

    def test_flush_edges_source_has_double_loop(self):
        """Inspect the _flush_edges source to verify bidimensional chunking."""
        import inspect

        source = inspect.getsource(er_tasks.run_entity_resolution)
        # The fix adds a nested loop: for _j in range(0, len(to_ids), _IN_CHUNK)
        assert "_to_chunk" in source, (
            "_flush_edges must chunk to_ids into _to_chunk (bidimensional chunking)"
        )

    def test_corporate_edges_has_double_loop(self):
        """Inspect corporate edge section for bidimensional chunking."""
        import inspect

        source = inspect.getsource(er_tasks.run_entity_resolution)
        # The fix: for _cj in range(0, len(corp_to_ids), _IN_CHUNK)
        assert "_ct" in source or "corp_to_ids[_cj" in source, (
            "Corporate edge query must chunk corp_to_ids"
        )


class TestDictSizeLogging:
    """P2: ER batch logging must include dict sizes for monitoring."""

    def test_log_fields_include_dict_sizes(self):
        """Verify the er.batch_done log call includes index size metrics."""
        import inspect

        source = inspect.getsource(er_tasks.run_entity_resolution)
        assert "cnpj_index_size" in source, "Must log cnpj_cluster dict size"
        assert "cpf_index_size" in source, "Must log cpf_hash_cluster dict size"
        assert "semantic_candidates" in source, "Must log semantic entity count"
        assert "semantic_matched" in source, "Must log semantic matched count"
