"""Tests for semantic signal deduplication in run_single_signal.

Covers:
- LLM_PROVIDER=none skips semantic dedup
- Semantically similar signal is deduped
- Dissimilar signal is created normally
- embed_signal_summary called after new signal creation
- Zero-vector embedding skips dedup check
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.tasks.signal_tasks import run_single_signal


def _make_savepoint():
    """Return a callable that produces an async context manager for session.begin_nested().

    AsyncMock children are also AsyncMock; calling begin_nested() returns a coroutine,
    not an async context manager.  This helper fixes that so the SAVEPOINT block works.
    """
    savepoint = MagicMock()
    savepoint.__aenter__ = AsyncMock(return_value=None)
    savepoint.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=savepoint)


def _make_fake_signal(summary="Test summary", severity_value="high"):
    """Build a fake signal returned by typology.run()."""
    signal = MagicMock()
    signal.entity_ids = [uuid.uuid4()]
    signal.event_ids = [uuid.uuid4()]
    signal.period_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    signal.period_end = datetime(2025, 6, 30, tzinfo=timezone.utc)
    signal.factors = {"ratio": 3.5}
    signal.confidence = 0.88
    signal.title = "Test Signal"
    signal.summary = summary
    signal.severity = MagicMock()
    signal.severity.value = severity_value

    ref = MagicMock()
    ref.url = "https://example.com/source"
    ref.ref_id = "ref-1"
    ref.source_hash = "abc"
    ref.snapshot_uri = None
    ref.model_dump.return_value = {"description": "Evidence", "url": "https://example.com/source"}
    signal.evidence_refs = [ref]

    return signal


def _make_fake_typology_with_signals(signals):
    """Build a fake typology that returns specific signals."""
    typology = MagicMock()
    typology.id = "T99"
    typology.name = "Test Typology"
    typology.required_domains = []
    typology.__class__.__doc__ = "Test doc"

    async def _run(session):
        return signals

    typology.run = _run
    return typology


class TestSemanticSignalDedup:
    def test_skips_when_provider_none(self):
        """LLM_PROVIDER=none: no embed call, signal persisted normally."""
        signal = _make_fake_signal()
        typology = _make_fake_typology_with_signals([signal])

        typ_row = MagicMock()
        typ_row.id = uuid.uuid4()

        call_count = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                # Typology row lookup
                result.scalar_one_or_none.return_value = typ_row
                return result
            else:
                # Dedup key lookup -> not found
                result.scalar_one_or_none.return_value = None
                return result

        mock_session = AsyncMock()
        mock_session.execute = _fake_execute
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin_nested = _make_savepoint()

        with patch("shared.typologies.registry.get_typology", return_value=typology), \
             patch("shared.db.async_session", return_value=mock_session), \
             patch("shared.config.settings") as mock_settings, \
             patch("worker.tasks.ai_tasks.explain_pending_signals"):
            mock_settings.LLM_PROVIDER = "none"
            mock_settings.OPENAI_MODEL = "gpt-4o"

            result = run_single_signal("T99")

        assert result["signals_created"] == 1
        assert result["signals_deduped"] == 0

    def test_deduplicates_semantically_similar_signal(self):
        """pgvector returns a match (distance <= 0.10): signal deduped."""
        signal = _make_fake_signal(summary="Concentrated vendor pattern")
        typology = _make_fake_typology_with_signals([signal])

        typ_row = MagicMock()
        typ_row.id = uuid.uuid4()

        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.1] * 1536]

        call_count = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                # Typology row lookup
                result.scalar_one_or_none.return_value = typ_row
                return result
            elif call_count["n"] == 2:
                # Dedup key lookup -> not found
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count["n"] == 3:
                # Semantic dedup query -> found a match!
                dup_row = MagicMock()
                result.first.return_value = dup_row
                return result
            return result

        mock_session = AsyncMock()
        mock_session.execute = _fake_execute
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.typologies.registry.get_typology", return_value=typology), \
             patch("shared.db.async_session", return_value=mock_session), \
             patch("shared.config.settings") as mock_settings, \
             patch("shared.ai.provider.get_llm_provider", return_value=mock_provider), \
             patch("worker.tasks.ai_tasks.explain_pending_signals"):
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.OPENAI_MODEL = "gpt-4o"

            result = run_single_signal("T99")

        assert result["signals_deduped"] == 1
        assert result["signals_created"] == 0

    def test_does_not_dedup_dissimilar_signal(self):
        """pgvector returns no match: signal is created normally."""
        signal = _make_fake_signal(summary="Unique new risk pattern")
        typology = _make_fake_typology_with_signals([signal])

        typ_row = MagicMock()
        typ_row.id = uuid.uuid4()

        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.5] * 1536]

        call_count = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                # Typology row lookup
                result.scalar_one_or_none.return_value = typ_row
                return result
            elif call_count["n"] == 2:
                # Dedup key lookup -> not found
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count["n"] == 3:
                # Semantic dedup -> no match
                result.first.return_value = None
                return result
            return result

        mock_session = AsyncMock()
        mock_session.execute = _fake_execute
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin_nested = _make_savepoint()

        with patch("shared.typologies.registry.get_typology", return_value=typology), \
             patch("shared.db.async_session", return_value=mock_session), \
             patch("shared.config.settings") as mock_settings, \
             patch("shared.ai.provider.get_llm_provider", return_value=mock_provider), \
             patch("shared.ai.embeddings.embed_signal_summary", new_callable=AsyncMock), \
             patch("worker.tasks.ai_tasks.explain_pending_signals"):
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.OPENAI_MODEL = "gpt-4o"

            result = run_single_signal("T99")

        assert result["signals_created"] == 1
        assert result["signals_deduped"] == 0

    def test_embeds_summary_after_creation(self):
        """New signal created: embed_signal_summary called with signal.id."""
        signal = _make_fake_signal(summary="New risk signal summary")
        typology = _make_fake_typology_with_signals([signal])

        typ_row = MagicMock()
        typ_row.id = uuid.uuid4()

        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.3] * 1536]

        call_count = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                # Typology row lookup
                result.scalar_one_or_none.return_value = typ_row
                return result
            elif call_count["n"] == 2:
                # Dedup key lookup -> not found
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count["n"] == 3:
                # Semantic dedup -> no match
                result.first.return_value = None
                return result
            return result

        mock_session = AsyncMock()
        mock_session.execute = _fake_execute
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin_nested = _make_savepoint()

        embed_calls = []

        async def _fake_embed_summary(session, signal_id, summary):
            embed_calls.append({"signal_id": signal_id, "summary": summary})

        with patch("shared.typologies.registry.get_typology", return_value=typology), \
             patch("shared.db.async_session", return_value=mock_session), \
             patch("shared.config.settings") as mock_settings, \
             patch("shared.ai.provider.get_llm_provider", return_value=mock_provider), \
             patch("shared.ai.embeddings.embed_signal_summary", side_effect=_fake_embed_summary), \
             patch("worker.tasks.ai_tasks.explain_pending_signals"):
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.OPENAI_MODEL = "gpt-4o"

            result = run_single_signal("T99")

        assert result["signals_created"] == 1
        assert len(embed_calls) == 1
        assert embed_calls[0]["summary"] == "New risk signal summary"

    def test_zero_vector_skips_dedup(self):
        """embed returns all zeros (LLM disabled for embed): no dedup check performed."""
        signal = _make_fake_signal(summary="Summary text")
        typology = _make_fake_typology_with_signals([signal])

        typ_row = MagicMock()
        typ_row.id = uuid.uuid4()

        mock_provider = AsyncMock()
        # Returns zero vectors (fallback when no embeddings available)
        mock_provider.embed.return_value = [[0.0] * 1536]

        call_count = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                # Typology row lookup
                result.scalar_one_or_none.return_value = typ_row
                return result
            elif call_count["n"] == 2:
                # Dedup key lookup -> not found
                result.scalar_one_or_none.return_value = None
                return result
            return result

        mock_session = AsyncMock()
        mock_session.execute = _fake_execute
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin_nested = _make_savepoint()

        with patch("shared.typologies.registry.get_typology", return_value=typology), \
             patch("shared.db.async_session", return_value=mock_session), \
             patch("shared.config.settings") as mock_settings, \
             patch("shared.ai.provider.get_llm_provider", return_value=mock_provider), \
             patch("shared.ai.embeddings.embed_signal_summary", new_callable=AsyncMock), \
             patch("worker.tasks.ai_tasks.explain_pending_signals"):
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.OPENAI_MODEL = "gpt-4o"

            result = run_single_signal("T99")

        # Signal created because zero vectors skip the semantic dedup check
        assert result["signals_created"] == 1
        assert result["signals_deduped"] == 0
