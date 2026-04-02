"""Corporate relationship edges derived from Receita Federal CNPJ entity attrs.

Builds graph edges that co-occurrence analysis cannot detect:
- SAME_ADDRESS  : two or more companies share the same registered address
- SHARES_PHONE  : two or more companies share the same phone number
- SAME_SOCIO    : two or more companies share a QSA partner (by CPF/CNPJ)
- SAME_ACCOUNTANT: two or more companies share the same registered accountant (CNPJ)
- SUBSIDIARY / HOLDING: same CNPJ raiz (first 8 digits) → branch relationship

These edge types unlock T13 (conflict of interest) and T17 (layered money
laundering) which require corporate network topology, not just event co-occurrence.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass

_IN_CHUNK = 5_000


@dataclass
class CorporateEdge:
    from_entity_id: uuid.UUID
    to_entity_id: uuid.UUID
    edge_type: str        # SAME_ADDRESS | SHARES_PHONE | SAME_SOCIO | SAME_ACCOUNTANT | SUBSIDIARY | HOLDING
    weight: float
    verification_method: str
    verification_confidence: float
    attrs: dict


def _digits_only(value: object) -> str:
    return "".join(c for c in str(value or "") if c.isdigit())


def _cnpj_raiz(cnpj: str) -> str:
    digits = _digits_only(cnpj)
    return digits[:8] if len(digits) >= 8 else ""


def _normalise_address(raw: object) -> str:
    text = str(raw or "").strip().upper()
    # Remove common noise words so minor formatting differences don't prevent matching
    for noise in (" DE ", " DA ", " DO ", " DAS ", " DOS ", ",", ".", "-"):
        text = text.replace(noise, " ")
    return " ".join(text.split())  # collapse whitespace


def _normalise_phone(raw: object) -> str:
    return _digits_only(raw)


def build_corporate_edges(session) -> list[CorporateEdge]:
    """Build corporate relationship edges from entity attrs.

    Queries all entities with type='company' (or 'org') and groups them by
    shared structural attributes from Receita Federal CNPJ data.

    Returns a flat list of CorporateEdge objects. The caller (er_tasks.py) is
    responsible for materialising them as GraphEdge rows.
    """
    from sqlalchemy import select

    from openwatch_models.orm import Entity

    # Load all companies in batches to avoid loading millions of rows at once.
    # We only need id, identifiers, and attrs.
    address_index: dict[str, list[uuid.UUID]] = defaultdict(list)
    phone_index: dict[str, list[uuid.UUID]] = defaultdict(list)
    socio_index: dict[str, list[uuid.UUID]] = defaultdict(list)   # cpf/cnpj → [entity_id]
    accountant_index: dict[str, list[uuid.UUID]] = defaultdict(list)
    cnpj_raiz_index: dict[str, list[uuid.UUID]] = defaultdict(list)

    offset = 0
    while True:
        rows = session.execute(
            select(Entity.id, Entity.identifiers, Entity.attrs)
            .where(Entity.type.in_(["company", "org"]))
            .order_by(Entity.id)
            .limit(_IN_CHUNK)
            .offset(offset)
        ).all()

        if not rows:
            break

        for entity_id, identifiers, attrs in rows:
            a = attrs or {}
            idents = identifiers or {}

            # Address index
            raw_addr = a.get("address") or a.get("logradouro") or a.get("endereco")
            if raw_addr:
                norm = _normalise_address(raw_addr)
                if len(norm) > 15:  # ignore very short/uninformative addresses
                    address_index[norm].append(entity_id)

            # Phone index
            raw_phone = a.get("telefone") or a.get("phone") or a.get("fone")
            if raw_phone:
                norm_phone = _normalise_phone(raw_phone)
                if len(norm_phone) >= 8:
                    phone_index[norm_phone].append(entity_id)

            # QSA (quadro societário) → SAME_SOCIO
            qsa: list = a.get("qsa") or []
            if isinstance(qsa, list):
                for socio in qsa:
                    if not isinstance(socio, dict):
                        continue
                    socio_id = (
                        _digits_only(socio.get("cpf_cnpj_socio") or socio.get("cpf") or socio.get("cnpj") or "")
                    )
                    if len(socio_id) >= 11:
                        socio_index[socio_id].append(entity_id)

            # Accountant (CNPJ do contabilista)
            accountant_cnpj = _digits_only(
                a.get("cnpj_contabilista") or a.get("contabilista_cnpj") or ""
            )
            if len(accountant_cnpj) == 14:
                accountant_index[accountant_cnpj].append(entity_id)

            # CNPJ raiz → SUBSIDIARY / HOLDING
            cnpj_raw = idents.get("cnpj") or a.get("cnpj") or ""
            raiz = _cnpj_raiz(cnpj_raw)
            if raiz:
                cnpj_raiz_index[raiz].append(entity_id)

        offset += _IN_CHUNK

    edges: list[CorporateEdge] = []

    # ── SAME_ADDRESS edges ────────────────────────────────────────────────────
    for address, entity_ids in address_index.items():
        unique_ids = list(dict.fromkeys(entity_ids))  # dedup preserving order
        if len(unique_ids) < 2:
            continue
        for i in range(len(unique_ids)):
            for j in range(i + 1, len(unique_ids)):
                edges.append(CorporateEdge(
                    from_entity_id=unique_ids[i],
                    to_entity_id=unique_ids[j],
                    edge_type="SAME_ADDRESS",
                    weight=1.0,
                    verification_method="shared_address",
                    verification_confidence=0.60,
                    attrs={"address": address},
                ))

    # ── SHARES_PHONE edges ────────────────────────────────────────────────────
    for phone, entity_ids in phone_index.items():
        unique_ids = list(dict.fromkeys(entity_ids))
        if len(unique_ids) < 2:
            continue
        for i in range(len(unique_ids)):
            for j in range(i + 1, len(unique_ids)):
                edges.append(CorporateEdge(
                    from_entity_id=unique_ids[i],
                    to_entity_id=unique_ids[j],
                    edge_type="SHARES_PHONE",
                    weight=1.5,
                    verification_method="shared_phone",
                    verification_confidence=0.65,
                    attrs={"phone": phone},
                ))

    # ── SAME_SOCIO edges ──────────────────────────────────────────────────────
    for socio_id, entity_ids in socio_index.items():
        unique_ids = list(dict.fromkeys(entity_ids))
        if len(unique_ids) < 2:
            continue
        for i in range(len(unique_ids)):
            for j in range(i + 1, len(unique_ids)):
                edges.append(CorporateEdge(
                    from_entity_id=unique_ids[i],
                    to_entity_id=unique_ids[j],
                    edge_type="SAME_SOCIO",
                    weight=2.5,
                    verification_method="shared_qsa_partner",
                    verification_confidence=0.85,
                    attrs={"socio_cpf_cnpj": socio_id},
                ))

    # ── SAME_ACCOUNTANT edges ─────────────────────────────────────────────────
    for acct_cnpj, entity_ids in accountant_index.items():
        unique_ids = list(dict.fromkeys(entity_ids))
        if len(unique_ids) < 2:
            continue
        for i in range(len(unique_ids)):
            for j in range(i + 1, len(unique_ids)):
                edges.append(CorporateEdge(
                    from_entity_id=unique_ids[i],
                    to_entity_id=unique_ids[j],
                    edge_type="SAME_ACCOUNTANT",
                    weight=1.0,
                    verification_method="shared_accountant",
                    verification_confidence=0.55,
                    attrs={"accountant_cnpj": acct_cnpj},
                ))

    # ── SUBSIDIARY / HOLDING edges ────────────────────────────────────────────
    for raiz, entity_ids in cnpj_raiz_index.items():
        unique_ids = list(dict.fromkeys(entity_ids))
        if len(unique_ids) < 2:
            continue
        # First entity (lowest UUID sort) treated as possible holding/parent;
        # all others are subsidiaries.  We add bidirectional pairs with
        # SUBSIDIARY from child→parent and HOLDING from parent→child so T17
        # cycle detection can traverse in both directions.
        sorted_ids = sorted(unique_ids, key=str)
        parent = sorted_ids[0]
        for child in sorted_ids[1:]:
            edges.append(CorporateEdge(
                from_entity_id=child,
                to_entity_id=parent,
                edge_type="SUBSIDIARY",
                weight=2.0,
                verification_method="cnpj_raiz_match",
                verification_confidence=0.90,
                attrs={"cnpj_raiz": raiz},
            ))
            edges.append(CorporateEdge(
                from_entity_id=parent,
                to_entity_id=child,
                edge_type="HOLDING",
                weight=2.0,
                verification_method="cnpj_raiz_match",
                verification_confidence=0.90,
                attrs={"cnpj_raiz": raiz},
            ))

    return edges
