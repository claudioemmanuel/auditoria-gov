"""Tests for new AI task functions: embed_entities_batch, classify_texts_unclassified, explain_pending_signals.

Covers:
- embed_entities_batch: skip on LLM_PROVIDER=none, batch embedding, graceful error handling
- classify_texts_unclassified: skip on LLM_PROVIDER=none, classification, empty results
- explain_pending_signals: session passed to explain_signal, async_session used
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import shared.db  # noqa: F401 — ensure module is cached before settings is patched

from worker.tasks.ai_tasks import (
    classify_texts_unclassified,
    embed_entities_batch,
    explain_pending_signals,
)


class TestEmbedEntitiesBatch:
    def test_skips_when_provider_none(self):
        """LLM_PROVIDER=none: returns status=skipped without any embedding calls."""
        with patch("shared.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "none"
            result = embed_entities_batch([
                {"entity_id": str(uuid.uuid4()), "name_normalized": "test"},
            ])

        assert result == {"status": "skipped"}

    def test_embeds_batch(self):
        """Mocks embed_entity, verifies called for each item, commits."""
        items = [
            {"entity_id": str(uuid.uuid4()), "name_normalized": "empresa alfa"},
            {"entity_id": str(uuid.uuid4()), "name_normalized": "empresa beta"},
        ]

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        embed_calls = []

        async def _fake_embed(session, entity_id, name):
            embed_calls.append({"entity_id": entity_id, "name": name})

        with patch("shared.config.settings") as mock_settings, \
             patch("shared.db.async_session", return_value=mock_session), \
             patch("shared.ai.embeddings.embed_entity", side_effect=_fake_embed):
            mock_settings.LLM_PROVIDER = "openai"
            result = embed_entities_batch(items)

        assert result["status"] == "completed"
        assert result["embedded"] == 2
        assert len(embed_calls) == 2
        mock_session.commit.assert_awaited_once()

    def test_graceful_on_error(self):
        """One item raises exception: others still processed, returns completed."""
        items = [
            {"entity_id": str(uuid.uuid4()), "name_normalized": "good entity"},
            {"entity_id": str(uuid.uuid4()), "name_normalized": "bad entity"},
            {"entity_id": str(uuid.uuid4()), "name_normalized": "another good"},
        ]

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        call_num = {"n": 0}

        async def _fake_embed(session, entity_id, name):
            call_num["n"] += 1
            if call_num["n"] == 2:
                raise RuntimeError("Embedding failed")

        with patch("shared.config.settings") as mock_settings, \
             patch("shared.db.async_session", return_value=mock_session), \
             patch("shared.ai.embeddings.embed_entity", side_effect=_fake_embed):
            mock_settings.LLM_PROVIDER = "openai"
            result = embed_entities_batch(items)

        assert result["status"] == "completed"
        # 2 succeeded, 1 failed
        assert result["embedded"] == 2


class TestClassifyTextsUnclassified:
    def test_skips_when_provider_none(self):
        """LLM_PROVIDER=none: returns status=skipped."""
        with patch("shared.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "none"
            result = classify_texts_unclassified()

        assert result == {"status": "skipped"}

    def test_classifies_found_texts(self):
        """Mocks classify_text, verifies attrs updated with classification."""
        tc1 = MagicMock()
        tc1.id = uuid.uuid4()
        tc1.content = "Compra de material de escritorio"
        tc1.attrs = {}

        tc2 = MagicMock()
        tc2.id = uuid.uuid4()
        tc2.content = "Servico de limpeza"
        tc2.attrs = {}

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = [tc1, tc2]

        async def _fake_classify(content, categories):
            if "escritorio" in content:
                return "compras"
            return "servicos"

        with patch("shared.config.settings") as mock_settings, \
             patch("shared.db_sync.SyncSession", return_value=mock_session), \
             patch("shared.ai.classify.classify_text", side_effect=_fake_classify):
            mock_settings.LLM_PROVIDER = "openai"
            result = classify_texts_unclassified()

        assert result["status"] == "completed"
        assert result["classified"] == 2
        assert tc1.attrs["classification"] == "compras"
        assert tc2.attrs["classification"] == "servicos"
        mock_session.commit.assert_called_once()

    def test_handles_empty_result(self):
        """No unclassified texts: returns classified=0."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        with patch("shared.config.settings") as mock_settings, \
             patch("shared.db_sync.SyncSession", return_value=mock_session):
            mock_settings.LLM_PROVIDER = "openai"
            result = classify_texts_unclassified()

        assert result["status"] == "completed"
        assert result["classified"] == 0


class TestExplainPendingSignals:
    def test_passes_session_to_explain_signal(self):
        """Verify session is now passed to explain_signal."""
        fake_typology = MagicMock()
        fake_typology.code = "T01"
        fake_typology.name = "Test"

        fake_signal = MagicMock()
        fake_signal.id = uuid.uuid4()
        fake_signal.typology = fake_typology
        fake_signal.severity = "high"
        fake_signal.confidence = 0.9
        fake_signal.title = "Test Signal"
        fake_signal.factors = {"x": 1}
        fake_signal.evidence_refs = []
        fake_signal.explanation_md = None

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [fake_signal]
        mock_session.execute = AsyncMock(return_value=mock_result)

        explain_kwargs_list = []

        async def _fake_explain(**kwargs):
            explain_kwargs_list.append(kwargs)
            return "# Explanation"

        with patch("shared.db.async_session", return_value=mock_session), \
             patch("shared.ai.explain.explain_signal", side_effect=_fake_explain):
            result = explain_pending_signals()

        assert result["status"] == "completed"
        assert result["explained"] == 1
        assert len(explain_kwargs_list) == 1
        assert "session" in explain_kwargs_list[0]
        assert explain_kwargs_list[0]["session"] is mock_session

    def test_async_session_used(self):
        """Verify async_session (not SyncSession) is used."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        async_session_called = {"value": False}

        def _fake_async_session():
            async_session_called["value"] = True
            return mock_session

        with patch("shared.db.async_session", side_effect=_fake_async_session):
            explain_pending_signals()

        assert async_session_called["value"] is True
