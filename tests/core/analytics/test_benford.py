import math

import pytest

from openwatch_analytics.benford import (
    BENFORD_EXPECTED,
    BenfordResult,
    _extract_first_digit,
    benford_test,
)


class TestExtractFirstDigit:
    def test_simple_integer(self):
        assert _extract_first_digit(5) == 5

    def test_large_number(self):
        assert _extract_first_digit(12345) == 1

    def test_small_decimal(self):
        assert _extract_first_digit(0.00789) == 7

    def test_zero_returns_none(self):
        assert _extract_first_digit(0) is None

    def test_negative_returns_none(self):
        assert _extract_first_digit(-5) is None

    def test_one(self):
        assert _extract_first_digit(1) == 1

    def test_nine(self):
        assert _extract_first_digit(9) == 9

    def test_hundred(self):
        assert _extract_first_digit(100) == 1

    def test_very_large(self):
        assert _extract_first_digit(9_999_999) == 9


class TestBenfordExpected:
    def test_sums_to_one(self):
        total = sum(BENFORD_EXPECTED.values())
        assert abs(total - 1.0) < 1e-10

    def test_digit_1_is_highest(self):
        assert BENFORD_EXPECTED[1] > BENFORD_EXPECTED[2]

    def test_digit_9_is_lowest(self):
        assert BENFORD_EXPECTED[9] < BENFORD_EXPECTED[8]

    def test_all_digits_present(self):
        for d in range(1, 10):
            assert d in BENFORD_EXPECTED


class TestBenfordTest:
    def test_insufficient_data(self):
        result = benford_test([1, 2, 3])
        assert result.sample_size == 3
        assert result.mad_classification == "insufficient_data"
        assert not result.flagged

    def test_benford_conforming_data(self):
        """Generate data following Benford's law.

        Uses large sample to ensure statistical conformity.
        """
        import random
        random.seed(42)
        # Generate values following Benford distribution
        values = []
        for _ in range(10000):
            # 10^U where U is uniform [0, 6] gives Benford-conforming first digits
            u = random.uniform(0, 6)
            values.append(10 ** u)

        result = benford_test(values)
        assert result.sample_size == 10000
        # With large sample, p-values should indicate conformity
        assert result.p_value_chi2 > 0.01
        assert result.p_value_ks > 0.01

    def test_uniform_data_non_conforming(self):
        """Uniform distribution should not conform to Benford."""
        import random
        random.seed(42)
        values = [random.uniform(1, 9) for _ in range(1000)]

        result = benford_test(values)
        assert result.sample_size == 1000
        # Uniform data deviates from Benford
        assert result.mad_score > 0

    def test_all_same_digit_non_conforming(self):
        """All values starting with same digit should be non-conforming."""
        values = [float(f"5{i:04d}") for i in range(100)]

        result = benford_test(values)
        assert result.flagged
        assert result.mad_classification == "non-conforming"

    def test_result_has_distributions(self):
        values = list(range(1, 200))
        result = benford_test(values)
        assert len(result.digit_distribution) == 9
        assert len(result.expected_distribution) == 9

    def test_digit_distribution_sums_to_one(self):
        values = list(range(1, 200))
        result = benford_test(values)
        total = sum(result.digit_distribution.values())
        assert abs(total - 1.0) < 0.01


class TestBenfordResult:
    def test_dataclass_fields(self):
        result = BenfordResult(
            conformity_score=0.8,
            p_value_chi2=0.05,
            p_value_ks=0.1,
            mad_score=0.001,
            mad_classification="close",
            digit_distribution={1: 0.301},
            expected_distribution={1: 0.301},
            sample_size=100,
            flagged=False,
        )
        assert result.conformity_score == 0.8
        assert result.sample_size == 100
        assert not result.flagged
