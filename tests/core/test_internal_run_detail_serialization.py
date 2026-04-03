import json

from api.app.routers import internal


def test_preview_text_serializes_nested_object_as_json():
    """Regression: field examples for nested payloads must not use Python repr."""
    mandato_payload = {
        "Titular": {
            "NomeParlamentar": "Jarbas Vasconcelos",
            "CodigoParlamentar": "4545",
            "DescricaoParticipacao": "Titular",
        },
        "CodigoMandato": "526",
    }

    preview = internal._preview_text(internal._compact_nested(mandato_payload))
    parsed = json.loads(preview)

    assert isinstance(parsed, dict)
    assert parsed["CodigoMandato"] == "526"
    assert parsed["Titular"]["NomeParlamentar"] == "Jarbas Vasconcelos"


def test_preview_text_serializes_list_summary_as_json():
    """Regression: compacted arrays must be serialized as JSON in field examples."""
    telefone_payload = [{"NumeroTelefone": "33033522"}, {"NumeroTelefone": "33033523"}]

    preview = internal._preview_text(internal._compact_nested(telefone_payload))
    parsed = json.loads(preview)

    assert parsed["items"] == 2
    assert parsed["first"]["NumeroTelefone"] == "33033522"
