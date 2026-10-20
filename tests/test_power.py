"""문서의 예시 계산과 statsmodels 결과를 둘 다 맞추는지 확인한다."""
import pytest
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

from playbook import (
    bonferroni_alpha,
    days_needed,
    familywise_error,
    mde_given_n,
    power_given_n,
    sample_size_per_group,
)


def test_doc_example_about_14750_per_group():
    # 문서 5절: 대조군 10%, MDE +1%p, alpha .05, 검정력 .8 → 그룹당 약 1만 4,750명
    n = sample_size_per_group(0.10, 0.01)
    assert 14_700 <= n <= 14_800


def test_halving_mde_needs_about_four_times_sample():
    # 문서 6절: 차이를 절반으로 줄이면 표본은 약 4배
    ratio = sample_size_per_group(0.10, 0.005) / sample_size_per_group(0.10, 0.01)
    assert 3.6 < ratio < 4.1


def test_power_is_inverse_of_sample_size():
    n = sample_size_per_group(0.10, 0.01)
    assert power_given_n(0.10, 0.01, n) == pytest.approx(0.80, abs=0.005)


def test_mde_is_inverse_of_sample_size():
    n = sample_size_per_group(0.10, 0.01)
    assert mde_given_n(0.10, n) == pytest.approx(0.01, abs=0.0002)


def test_close_to_statsmodels_arcsine_method():
    # statsmodels는 arcsine 변환(Cohen's h)을 써서 값이 조금 다르다. 2% 안이면 같은 답으로 본다
    h = proportion_effectsize(0.11, 0.10)
    n_sm = NormalIndPower().solve_power(effect_size=h, alpha=0.05, power=0.8, ratio=1)
    assert sample_size_per_group(0.10, 0.01) == pytest.approx(n_sm, rel=0.02)


def test_days_needed():
    assert days_needed(14_750, daily_assigned_total=5_000) == 6


def test_multiple_comparisons():
    # 문서 7절: 5%로 3번 비교하면 거짓양성 약 14%, 본페로니면 쌍마다 약 1.67%
    assert familywise_error(0.05, 3) == pytest.approx(0.1426, abs=0.001)
    assert bonferroni_alpha(0.05, 3) == pytest.approx(0.0167, abs=0.0001)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        sample_size_per_group(0.10, 0)
    with pytest.raises(ValueError):
        sample_size_per_group(0.95, 0.10)
