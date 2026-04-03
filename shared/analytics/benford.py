"""Benford's Law analysis for detecting anomalous number distributions.

Benford's Law states that in many naturally occurring datasets,
the leading digit d occurs with probability log10(1 + 1/d).
Non-conformity may indicate data manipulation.

Implements:
- First-digit distribution extraction
- Chi-squared goodness of fit
- Kolmogorov-Smirnov test
- Mean Absolute Deviation (MAD) per Nigrini's classification
"""

import math
from dataclasses import dataclass, field


@dataclass
class BenfordResult:
    """Result of Benford's Law conformity analysis."""

    conformity_score: float  # 0.0 (non-conforming) to 1.0 (conforming)
    p_value_chi2: float  # Chi-squared p-value
    p_value_ks: float  # KS test p-value
    mad_score: float  # Mean Absolute Deviation
    mad_classification: str  # "close", "acceptable", "marginally", "non-conforming"
    digit_distribution: dict[int, float]  # Observed proportions
    expected_distribution: dict[int, float]  # Benford expected proportions
    sample_size: int
    flagged: bool  # True if non-conforming


# Expected Benford distribution for first digits 1-9
BENFORD_EXPECTED: dict[int, float] = {
    d: math.log10(1 + 1 / d) for d in range(1, 10)
}

# MAD thresholds (Nigrini, 2012)
_MAD_CLOSE = 0.0006
_MAD_ACCEPTABLE = 0.0012
_MAD_MARGINALLY = 0.0015
_MAD_NON_CONFORMING = 0.0022


def _extract_first_digit(value: float) -> int | None:
    """Extract the first significant digit from a number."""
    if value <= 0:
        return None
    # Handle very small or very large numbers via string conversion
    s = f"{value:.10e}"
    for c in s:
        if c.isdigit() and c != "0":
            return int(c)
    return None


def benford_test(values: list[float]) -> BenfordResult:
    """Run Benford's Law analysis on a list of values.

    Args:
        values: List of positive numerical values to analyze.

    Returns:
        BenfordResult with conformity metrics and classification.
    """
    # Extract first digits
    digits: list[int] = []
    for v in values:
        d = _extract_first_digit(abs(v))
        if d is not None:
            digits.append(d)

    n = len(digits)
    if n < 30:
        return BenfordResult(
            conformity_score=0.0,
            p_value_chi2=0.0,
            p_value_ks=0.0,
            mad_score=0.0,
            mad_classification="insufficient_data",
            digit_distribution={},
            expected_distribution=dict(BENFORD_EXPECTED),
            sample_size=n,
            flagged=False,
        )

    # Compute observed distribution
    digit_counts: dict[int, int] = {d: 0 for d in range(1, 10)}
    for d in digits:
        digit_counts[d] = digit_counts.get(d, 0) + 1

    observed: dict[int, float] = {
        d: count / n for d, count in digit_counts.items()
    }

    # MAD (Mean Absolute Deviation)
    mad = sum(
        abs(observed.get(d, 0) - BENFORD_EXPECTED[d]) for d in range(1, 10)
    ) / 9

    # MAD classification (Nigrini)
    if mad <= _MAD_CLOSE:
        mad_class = "close"
    elif mad <= _MAD_ACCEPTABLE:
        mad_class = "acceptable"
    elif mad <= _MAD_MARGINALLY:
        mad_class = "marginally"
    else:
        mad_class = "non-conforming"

    # Chi-squared test
    chi2_stat = 0.0
    for d in range(1, 10):
        expected_count = BENFORD_EXPECTED[d] * n
        observed_count = digit_counts.get(d, 0)
        if expected_count > 0:
            chi2_stat += (observed_count - expected_count) ** 2 / expected_count

    # Approximate p-value for chi-squared with 8 degrees of freedom
    p_value_chi2 = _chi2_survival(chi2_stat, df=8)

    # KS test (max deviation)
    cumulative_obs = 0.0
    cumulative_exp = 0.0
    max_diff = 0.0
    for d in range(1, 10):
        cumulative_obs += observed.get(d, 0)
        cumulative_exp += BENFORD_EXPECTED[d]
        diff = abs(cumulative_obs - cumulative_exp)
        if diff > max_diff:
            max_diff = diff

    # KS p-value approximation
    ks_stat = max_diff * math.sqrt(n)
    p_value_ks = _ks_survival(ks_stat)

    # Conformity score: inverse of MAD, normalized
    conformity = max(0.0, 1.0 - mad / _MAD_NON_CONFORMING)

    flagged = mad > _MAD_NON_CONFORMING

    return BenfordResult(
        conformity_score=round(conformity, 4),
        p_value_chi2=round(p_value_chi2, 6),
        p_value_ks=round(p_value_ks, 6),
        mad_score=round(mad, 6),
        mad_classification=mad_class,
        digit_distribution={d: round(v, 6) for d, v in observed.items()},
        expected_distribution={d: round(v, 6) for d, v in BENFORD_EXPECTED.items()},
        sample_size=n,
        flagged=flagged,
    )


def _chi2_survival(x: float, df: int) -> float:
    """Approximate chi-squared survival function (1 - CDF).

    Uses Wilson-Hilferty normal approximation for simplicity.
    For production, use scipy.stats.chi2.sf().
    """
    try:
        from scipy.stats import chi2
        return float(chi2.sf(x, df))
    except ImportError:
        pass

    # Fallback: Wilson-Hilferty approximation
    if x <= 0:
        return 1.0
    z = ((x / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    # Standard normal survival
    return 0.5 * math.erfc(z / math.sqrt(2))


def _ks_survival(ks_stat: float) -> float:
    """Approximate KS test survival function."""
    try:
        from scipy.stats import kstwobign
        return float(kstwobign.sf(ks_stat))
    except ImportError:
        pass

    # Rough approximation
    if ks_stat <= 0:
        return 1.0
    return max(0.0, math.exp(-2 * ks_stat ** 2))
