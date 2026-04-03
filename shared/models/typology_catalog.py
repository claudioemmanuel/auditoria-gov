"""Public typology catalog retained in the open-source layer.

This keeps safe, descriptive metadata for public `/tipologia*` endpoints without
shipping the private detection implementations that live in `openwatch-core`.
"""

from __future__ import annotations

from typing import Any

_TYPOS: dict[str, dict[str, Any]] = {
    "T01": {"name": "Concentração em Fornecedor", "corruption_types": ["fraude_licitatoria"], "spheres": ["administrativa"]},
    "T02": {"name": "Baixa Competição", "corruption_types": ["fraude_licitatoria"], "spheres": ["administrativa"]},
    "T03": {"name": "Fracionamento de Despesa", "corruption_types": ["fraude_licitatoria"], "spheres": ["administrativa"]},
    "T04": {"name": "Aditivo Outlier", "corruption_types": ["fraude_licitatoria", "corrupcao_passiva"], "spheres": ["administrativa"]},
    "T05": {"name": "Preço Outlier", "corruption_types": ["fraude_licitatoria"], "spheres": ["administrativa", "privada"]},
    "T06": {"name": "Proxy de Empresa de Fachada", "corruption_types": ["lavagem", "corrupcao_ativa"], "spheres": ["privada", "administrativa"]},
    "T07": {"name": "Rede de Cartel", "corruption_types": ["fraude_licitatoria", "corrupcao_ativa"], "spheres": ["privada", "sistemica"]},
    "T08": {"name": "Sanção x Contrato", "corruption_types": ["corrupcao_passiva", "prevaricacao"], "spheres": ["administrativa"]},
    "T09": {"name": "Proxy de Folha Fantasma", "corruption_types": ["peculato"], "spheres": ["administrativa"]},
    "T10": {"name": "Terceirização Paralela", "corruption_types": ["peculato", "fraude_licitatoria"], "spheres": ["administrativa"]},
    "T11": {"name": "Jogo de Planilha", "corruption_types": ["fraude_licitatoria", "peculato"], "spheres": ["administrativa", "privada"]},
    "T12": {"name": "Edital Direcionado", "corruption_types": ["fraude_licitatoria", "corrupcao_ativa_passiva"], "spheres": ["administrativa"]},
    "T13": {"name": "Conflito de Interesses", "corruption_types": ["nepotismo_clientelismo", "corrupcao_ativa_passiva"], "spheres": ["administrativa", "politica"]},
    "T14": {"name": "Sequência de Favorecimento Contratual", "corruption_types": ["corrupcao_ativa_passiva", "fraude_licitatoria"], "spheres": ["administrativa", "sistemica"]},
    "T15": {"name": "Inexigibilidade Indevida", "corruption_types": ["fraude_licitatoria", "prevaricacao"], "spheres": ["administrativa"]},
    "T16": {"name": "Clientelismo Orçamentário-Contratual", "corruption_types": ["nepotismo_clientelismo", "peculato"], "spheres": ["politica", "administrativa"]},
    "T17": {"name": "Lavagem via Camadas Societárias", "corruption_types": ["lavagem"], "spheres": ["privada", "sistemica"]},
    "T18": {"name": "Acúmulo Ilegal de Cargos", "corruption_types": ["peculato", "nepotismo_clientelismo"], "spheres": ["administrativa"]},
    "T19": {"name": "Rotação de Vencedores", "corruption_types": ["fraude_licitatoria"], "spheres": ["privada", "sistemica"]},
    "T20": {"name": "Licitantes Fantasmas", "corruption_types": ["fraude_licitatoria"], "spheres": ["privada"]},
    "T21": {"name": "Cluster Colusivo", "corruption_types": ["fraude_licitatoria"], "spheres": ["privada", "sistemica"]},
    "T22": {"name": "Favorecimento Político", "corruption_types": ["nepotismo_clientelismo", "corrupcao_ativa_passiva"], "spheres": ["politica", "privada"]},
}


def list_public_typologies() -> list[dict[str, Any]]:
    return [
        {
            "code": code,
            "name": meta["name"],
            "corruption_types": meta.get("corruption_types", []),
            "spheres": meta.get("spheres", []),
            "evidence_level": meta.get("evidence_level", ""),
            "description_legal": meta.get("description_legal", ""),
            "law_articles": meta.get("law_articles", []),
            "factors": meta.get("factors", []),
        }
        for code, meta in sorted(_TYPOS.items())
    ]


def get_public_typology(code: str) -> dict[str, Any] | None:
    upper = code.upper()
    meta = _TYPOS.get(upper)
    if meta is None:
        return None
    return {
        "code": upper,
        "name": meta["name"],
        "corruption_types": meta.get("corruption_types", []),
        "spheres": meta.get("spheres", []),
        "evidence_level": meta.get("evidence_level", ""),
        "description_legal": meta.get("description_legal", ""),
        "law_articles": meta.get("law_articles", []),
        "factors": meta.get("factors", []),
    }
