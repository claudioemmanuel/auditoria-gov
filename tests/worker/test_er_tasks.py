import uuid

from worker.tasks import er_tasks


def _entity(
    name: str,
    entity_type: str = "company",
    identifiers: dict | None = None,
    attrs: dict | None = None,
):
    return {
        "id": uuid.uuid4(),
        "name": name,
        "type": entity_type,
        "identifiers": identifiers or {},
        "attrs": attrs or {},
    }


def test_build_deterministic_matches_groups_by_identifier():
    same_cnpj = "11.222.333/0001-81"
    entities = [
        _entity("Empresa A", identifiers={"cnpj": same_cnpj}),
        _entity("Empresa B", identifiers={"cnpj": same_cnpj}),
        _entity("Empresa C", identifiers={"cnpj": "99.888.777/0001-66"}),
    ]

    matches = er_tasks._build_deterministic_matches(entities)

    assert len(matches) == 1
    assert matches[0].match_type == "deterministic"
    assert "CNPJ match" in matches[0].reason


def test_build_probabilistic_matches_uses_blocking():
    entities = [
        _entity("EMPRESA ALFA LOGISTICA LTDA"),
        _entity("EMPRESA ALFA LOGISTICA"),
        _entity("ASSOCIACAO CULTURAL BETA"),
    ]

    matches = er_tasks._build_probabilistic_matches(entities, matched_ids=set())

    assert matches
    assert any(m.match_type == "probabilistic" for m in matches)


def test_should_run_probabilistic_respects_entity_volume_limit():
    assert er_tasks._should_run_probabilistic(1000) is True
    assert er_tasks._should_run_probabilistic(6000) is False
