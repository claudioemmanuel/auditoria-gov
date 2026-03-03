import pytest

from shared.baselines.compute import _percentile, compute_metrics, _broaden_scope
from shared.baselines.models import BaselineType, MIN_SAMPLE_SIZE


class TestPercentile:
    def test_p50_is_median(self):
        data = sorted([1, 2, 3, 4, 5])
        assert _percentile(data, 50) == 3.0

    def test_p0_is_min(self):
        data = sorted([10, 20, 30])
        assert _percentile(data, 0) == 10.0

    def test_p100_is_max(self):
        data = sorted([10, 20, 30])
        assert _percentile(data, 100) == 30.0

    def test_empty_list(self):
        assert _percentile([], 50) == 0.0

    def test_single_element(self):
        assert _percentile([42], 50) == 42.0
        assert _percentile([42], 0) == 42.0
        assert _percentile([42], 100) == 42.0

    def test_interpolation(self):
        data = sorted([1, 2, 3, 4])
        result = _percentile(data, 25)
        assert result == 1.75  # Linear interpolation

    def test_p95(self):
        data = list(range(1, 101))  # 1 to 100
        result = _percentile(data, 95)
        assert result > 94


class TestComputeMetrics:
    def test_sufficient_sample(self):
        values = list(range(1, 51))  # 50 items
        result = compute_metrics(values, BaselineType.PRICE_BY_ITEM, "test_scope")
        assert result is not None
        assert result.sample_size == 50
        assert result.baseline_type == BaselineType.PRICE_BY_ITEM
        assert result.scope_key == "test_scope"

    def test_below_min_sample(self):
        values = list(range(1, 10))  # 9 items < MIN_SAMPLE_SIZE
        result = compute_metrics(values, BaselineType.PRICE_BY_ITEM, "test")
        assert result is None

    def test_exactly_min_sample(self):
        values = list(range(1, MIN_SAMPLE_SIZE + 1))
        result = compute_metrics(values, BaselineType.PRICE_BY_ITEM, "test")
        assert result is not None
        assert result.sample_size == MIN_SAMPLE_SIZE

    def test_mean_correct(self):
        values = [10.0] * 50
        result = compute_metrics(values, BaselineType.PRICE_BY_ITEM, "test")
        assert result is not None
        assert result.mean == 10.0

    def test_median_correct(self):
        values = list(range(1, 51))
        result = compute_metrics(values, BaselineType.PRICE_BY_ITEM, "test")
        assert result is not None
        assert result.median == 25.5

    def test_std_zero_for_identical(self):
        values = [5.0] * 50
        result = compute_metrics(values, BaselineType.PRICE_BY_ITEM, "test")
        assert result is not None
        assert result.std == 0.0

    def test_min_max(self):
        values = list(range(1, 51))
        result = compute_metrics(values, BaselineType.PRICE_BY_ITEM, "test")
        assert result is not None
        assert result.min_val == 1
        assert result.max_val == 50

    def test_percentiles_ordered(self):
        values = list(range(1, 101))
        result = compute_metrics(values, BaselineType.PRICE_BY_ITEM, "test")
        assert result is not None
        assert result.p5 <= result.p10 <= result.p25 <= result.median
        assert result.median <= result.p75 <= result.p90 <= result.p95 <= result.p99

    def test_two_values_std(self):
        """Two values gives valid std."""
        values = [1.0, 2.0] * 15  # 30 items
        result = compute_metrics(values, BaselineType.PRICE_BY_ITEM, "test")
        assert result is not None
        assert result.std > 0


class TestBroadenScope:
    def test_catmat_group_to_class(self):
        result = _broaden_scope("catmat_group::12345")
        assert result == "catmat_class::all"

    def test_catmat_class_to_modality(self):
        result = _broaden_scope("catmat_class::123")
        assert result == "modality::all"

    def test_modality_to_national(self):
        result = _broaden_scope("modality::pregao")
        assert result == "national::all"

    def test_national_returns_none(self):
        result = _broaden_scope("national::all")
        assert result is None

    def test_unknown_scope_returns_none(self):
        result = _broaden_scope("unknown::xyz")
        assert result is None

    def test_single_part_returns_none(self):
        result = _broaden_scope("nodelimiter")
        assert result is None


class TestBaselineModels:
    def test_baseline_type_enum(self):
        assert BaselineType.PRICE_BY_ITEM == "PRICE_BY_ITEM"
        assert BaselineType.PARTICIPANTS_PER_PROCUREMENT == "PARTICIPANTS_PER_PROCUREMENT"
        assert BaselineType.HHI_DISTRIBUTION == "HHI_DISTRIBUTION"
        assert BaselineType.AMENDMENT_DISTRIBUTION == "AMENDMENT_DISTRIBUTION"
        assert BaselineType.CONTRACT_DURATION == "CONTRACT_DURATION"

    def test_min_sample_size(self):
        assert MIN_SAMPLE_SIZE == 30
