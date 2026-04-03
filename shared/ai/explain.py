from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Template

from shared.ai.provider import explanatory_only, get_llm_provider
from shared.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

EXPLAIN_TEMPLATE = Template("""Você é um analista de controle público.

Analise o seguinte sinal de risco e produza uma explicação clara em português,
com evidências reproduzíveis. Use linguagem acessível ao cidadão.
{% if rag_context %}
## Sinais Similares (contexto histórico)
{{ rag_context }}
{% endif %}
## Sinal de Risco
- **Tipologia:** {{ typology_name }} ({{ typology_code }})
- **Severidade:** {{ severity }}
- **Confiança:** {{ confidence }}%
- **Título:** {{ title }}

## Fatores
{% for key, value in factors.items() %}
- **{{ key }}:** {{ value }}
{% endfor %}

## Evidências
{% for ref in evidence_refs %}
- {{ ref.description }}{% if ref.url %} — [fonte]({{ ref.url }}){% endif %}
{% endfor %}

## Instruções
1. Explique O QUE foi detectado.
2. Explique POR QUE isso é um indicador de risco.
3. Cite os dados específicos (valores, datas, entidades).
4. Inclua ressalva: "Este é um indicador estatístico, não uma acusação."
5. Formate em Markdown.""")

DETERMINISTIC_TEMPLATE = Template("""## {{ title }}

**Tipologia:** {{ typology_name }} ({{ typology_code }})
**Severidade:** {{ severity }} | **Confiança:** {{ confidence }}%

### O que foi detectado
Este sinal indica uma anomalia estatística do tipo "{{ typology_name }}"
identificada pela análise automatizada dos dados públicos.

### Fatores identificados
{% for key, value in factors.items() %}
- **{{ key }}:** {{ value }}
{% endfor %}

### Evidências
{% for ref in evidence_refs %}
- {{ ref.description }}
{% endfor %}

> **Nota:** Este é um indicador estatístico gerado automaticamente.
> Não constitui acusação ou prova de irregularidade.
> Recomenda-se análise aprofundada por órgão competente.""")


@explanatory_only
async def explain_signal(
    typology_code: str,
    typology_name: str,
    severity: str,
    confidence: float,
    title: str,
    factors: dict,
    evidence_refs: list[dict],
    session: AsyncSession | None = None,
) -> str:
    """Generate a markdown explanation for a risk signal.

    Uses LLM when available, falls back to deterministic Jinja2 template.
    When session is provided, enriches the prompt with RAG context from
    top-3 similar past signals stored in text_embedding.
    """
    context = {
        "typology_code": typology_code,
        "typology_name": typology_name,
        "severity": severity,
        "confidence": round(confidence * 100, 1),
        "title": title,
        "factors": factors,
        "evidence_refs": evidence_refs,
        "rag_context": "",
    }

    if settings.LLM_PROVIDER == "none":
        return DETERMINISTIC_TEMPLATE.render(**context)

    if session is not None:
        from shared.ai.rag import build_rag_context
        context["rag_context"] = await build_rag_context(title, session, max_tokens=500)

    prompt = EXPLAIN_TEMPLATE.render(**context)
    provider = get_llm_provider()
    return await provider.complete(prompt)
