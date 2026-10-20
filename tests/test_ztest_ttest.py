"""문서 z-vs-t.md의 예시 계산과 statsmodels, scipy 결과를 둘 다 맞추는지 확인한다."""
from math import sqrt

import pytest
from scipy.stats import norm, ttest_ind_from_stats
from statsmodels.stats import proportion as sm_proportion
from statsmodels.stats.proportion import proportions_ztest

from playbook import critical_value, student_ttest, two_proportion_ztest, welch_ttest


def test_critical_values_table():
    # 문서 판단 기준 2절 표
    assert critical_value() == pytest.approx(1.960, abs=0.001)
    assert critical_value(df=10) == pytest.approx(2.228, abs=0.001)
    assert critical_value(df=30) == pytest.approx(2.042, abs=0.001)
    assert critical_value(df=100) == pytest.approx(1.984, abs=0.001)
    assert critical_value(df=1_000) == pytest.approx(1.962, abs=0.001)
    assert critical_value(df=18) == pytest.approx(2.101, abs=0.001)


def test_doc_proportion_example():
    # 문서 4절: 1,000/10,000 vs 1,100/10,000 → z 2.307, p 0.0211
    z, p = two_proportion_ztest(1_000, 10_000, 1_100, 10_000)
    assert z == pytest.approx(2.307, abs=0.001)
    assert p == pytest.approx(0.0211, abs=0.0001)


def test_pooled_matches_statsmodels():
    z, p = two_proportion_ztest(1_000, 10_000, 1_100, 10_000)
    z_sm, p_sm = proportions_ztest([1_100, 1_000], [10_000, 10_000])
    assert z == pytest.approx(z_sm, rel=1e-9)
    assert p == pytest.approx(p_sm, rel=1e-9)


def test_unpooled_matches_statsmodels():
    z, _ = two_proportion_ztest(1_000, 10_000, 1_100, 10_000, pooled=False)
    # statsmodels에서 그룹별 비율로 분산을 잡는 건 wald 방식이다
    res = sm_proportion.test_proportions_2indep(1_100, 10_000, 1_000, 10_000, method="wald", compare="diff")
    assert z == pytest.approx(res.statistic, rel=1e-9)


def test_welch_on_binary_equals_ztest_at_scale():
    # 문서 4절: 0과 1 데이터에 Welch t를 써도 같은 답
    s0 = sqrt(0.10 * 0.90 * 10_000 / 9_999)
    s1 = sqrt(0.11 * 0.89 * 10_000 / 9_999)
    _, _, p_t = welch_ttest(0.10, s0, 10_000, 0.11, s1, 10_000)
    _, p_z = two_proportion_ztest(1_000, 10_000, 1_100, 10_000)
    assert p_t == pytest.approx(p_z, abs=0.0002)


def test_small_sample_flips_decision():
    # 안티패턴 2: 그룹당 10명이면 z는 유의, t는 유의하지 않음
    stat, df, p_t = welch_ttest(50, 9, 10, 58, 9, 10)
    p_z = 2 * norm.sf(stat)
    assert stat == pytest.approx(1.988, abs=0.001)
    assert df == pytest.approx(18, abs=0.01)
    assert p_z == pytest.approx(0.047, abs=0.001) and p_z < 0.05
    assert p_t == pytest.approx(0.062, abs=0.001) and p_t > 0.05


def test_welch_and_student_match_scipy():
    args = (104, 30, 100, 100, 10, 1_000)
    _, p_w_scipy = ttest_ind_from_stats(*args, equal_var=False)
    _, p_s_scipy = ttest_ind_from_stats(*args, equal_var=True)
    _, _, p_w = welch_ttest(100, 10, 1_000, 104, 30, 100)
    _, _, p_s = student_ttest(100, 10, 1_000, 104, 30, 100)
    assert p_w == pytest.approx(p_w_scipy, rel=1e-9)
    assert p_s == pytest.approx(p_s_scipy, rel=1e-9)
    # 안티패턴 3의 수치
    assert p_w == pytest.approx(0.188, abs=0.001)
    assert p_s == pytest.approx(0.004, abs=0.001)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        two_proportion_ztest(5, 0, 1, 10)
    with pytest.raises(ValueError):
        two_proportion_ztest(0, 10, 0, 10)
    with pytest.raises(ValueError):
        welch_ttest(1, 1, 1, 2, 1, 5)
