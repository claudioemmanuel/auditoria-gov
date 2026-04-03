from openwatch_typologies.factor_metadata import get_factor_descriptions


def test_get_factor_descriptions_t03_includes_current_keys():
    factors = {
        "n_purchases": 70,
        "ratio": 5.27,
        "avg_value_brl": 3767.81,
        "threshold_brl": 50000.0,
        "span_days": 0,
        "catmat_group": "unknown",
        "total_value_brl": 263746.63,
    }

    meta = get_factor_descriptions(factors, typology_code="T03")

    assert set(meta.keys()) == set(factors.keys())
    assert meta["n_purchases"]["label"] == "Compras no cluster"
    assert meta["ratio"]["label"] == "Razao valor/limite"
    assert meta["avg_value_brl"]["unit"] == "brl"
    assert meta["threshold_brl"]["unit"] == "brl"


def test_get_factor_descriptions_t03_overrides_generic_span_days_description():
    factors = {"span_days": 0}

    meta = get_factor_descriptions(factors, typology_code="T03")

    assert "janela temporal" in meta["span_days"]["description"].lower()
