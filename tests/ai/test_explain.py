from unittest.mock import AsyncMock, patch

import pytest

from shared.ai.explain import explain_signal


class TestExplainSignal:
    @pytest.mark.asyncio
    async def test_deterministic_template(self):
        result = await explain_signal(
            typology_code="T01",
            typology_name="Concentração em Fornecedor",
            severity="high",
            confidence=0.85,
            title="Alta concentração no órgão X",
            factors={"hhi": 0.95, "top1_share": "87%"},
            evidence_refs=[
                {"description": "Dados de licitações 2023-2024"}
            ],
        )
        assert isinstance(result, str)
        assert "T01" in result
        assert "Concentração em Fornecedor" in result
        assert "high" in result
        assert "85.0%" in result
        assert "hhi" in result
        assert "indicador estatístico" in result.lower()

    @pytest.mark.asyncio
    async def test_factors_rendered(self):
        result = await explain_signal(
            typology_code="T05",
            typology_name="Preço Outlier",
            severity="critical",
            confidence=0.92,
            title="Preço acima do p99",
            factors={"ratio": 5.2, "baseline_median": 100},
            evidence_refs=[],
        )
        assert "ratio" in result
        assert "5.2" in result

    @pytest.mark.asyncio
    async def test_evidence_rendered(self):
        result = await explain_signal(
            typology_code="T08",
            typology_name="Sanção x Contrato",
            severity="medium",
            confidence=0.7,
            title="Contrato com empresa sancionada",
            factors={},
            evidence_refs=[
                {"description": "Registro CEIS nº 12345"},
                {"description": "Contrato nº 67890"},
            ],
        )
        assert "Registro CEIS" in result
        assert "Contrato nº 67890" in result

    @pytest.mark.asyncio
    async def test_empty_factors_and_evidence(self):
        result = await explain_signal(
            typology_code="T02",
            typology_name="Baixa Competição",
            severity="low",
            confidence=0.5,
            title="Poucos participantes",
            factors={},
            evidence_refs=[],
        )
        assert isinstance(result, str)
        assert len(result) > 0


class TestExplainSignalWithLLM:
    @pytest.mark.asyncio
    async def test_openai_path(self):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "# Explicação LLM\nDetalhe."

        with patch("shared.ai.explain.settings") as mock_settings, \
             patch("shared.ai.explain.get_llm_provider", return_value=mock_provider):
            mock_settings.LLM_PROVIDER = "openai"

            result = await explain_signal(
                typology_code="T01",
                typology_name="Concentração",
                severity="high",
                confidence=0.9,
                title="Teste LLM",
                factors={"hhi": 0.8},
                evidence_refs=[{"description": "Dado X"}],
            )
            assert result == "# Explicação LLM\nDetalhe."
            mock_provider.complete.assert_awaited_once()
            prompt_arg = mock_provider.complete.call_args[0][0]
            assert "T01" in prompt_arg
            assert "Concentração" in prompt_arg
