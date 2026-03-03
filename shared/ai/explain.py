from jinja2 import Template

from shared.ai.provider import get_llm_provider
from shared.config import settings

EXPLAIN_TEMPLATE = Template("""Você é um analista de controle público.

Analise o seguinte sinal de risco e produza uma explicação clara em português,
com evidências reproduzíveis. Use linguagem acessível ao cidadão.

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


async def explain_signal(
    typology_code: str,
    typology_name: str,
    severity: str,
    confidence: float,
    title: str,
    factors: dict,
    evidence_refs: list[dict],
) -> str:
    """Generate a markdown explanation for a risk signal.

    Uses LLM when available, falls back to deterministic Jinja2 template.
    """
    context = {
        "typology_code": typology_code,
        "typology_name": typology_name,
        "severity": severity,
        "confidence": round(confidence * 100, 1),
        "title": title,
        "factors": factors,
        "evidence_refs": evidence_refs,
    }

    if settings.LLM_PROVIDER == "none":
        return DETERMINISTIC_TEMPLATE.render(**context)

    prompt = EXPLAIN_TEMPLATE.render(**context)
    provider = get_llm_provider()
    return await provider.complete(prompt)
