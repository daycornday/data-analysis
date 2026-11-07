"""문서의 예시 계산을 다시 하고, delta method 분산이 scipy, 선형화, 부트스트랩과 맞는지 확인한다."""
import numpy as np
import pytest
from scipy.stats import ttest_ind

from playbook import ratio_delta_var, ratio_ztest, relative_lift_ci, two_proportion_ztest


def simulate_users(rng, n, mean_impressions=10, ctr_a=2.0):
    # 문서와 그림 스크립트에서 쓰는 것과 같은 가상 데이터. 유저마다 노출 수와 클릭 성향이 다르다
    if mean_impressions > 1:
        imp = rng.negative_binomial(2, 2 / (2 + mean_impressions - 1), size=n) + 1
    else:
        imp = np.ones(n, dtype=int)
    ctr = rng.beta(ctr_a, 18, size=n)
    return rng.binomial(imp, ctr), imp


@pytest.fixture(scope="module")
def doc_example():
    rng = np.random.default_rng(27)
    c0, i0 = simulate_users(rng, 5_000)
    c1, i1 = simulate_users(rng, 5_000, ctr_a=2.1)
    return c0, i0, c1, i1


def test_doc_example_numbers(doc_example):
    c0, i0, c1, i1 = doc_example
    # 문서 판단 기준 2절 표
    assert (c0.sum(), i0.sum(), c1.sum(), i1.sum()) == (5_100, 50_770, 5_265, 50_289)
    _, p_naive = two_proportion_ztest(c0.sum(), i0.sum(), c1.sum(), i1.sum(), pooled=False)
    assert p_naive == pytest.approx(0.026, abs=0.0005)
    t = ratio_ztest(c0, i0, c1, i1)
    assert t.diff == pytest.approx(0.00424, abs=0.00001)
    assert t.se == pytest.approx(0.00248, abs=0.00001)
    assert t.p_value == pytest.approx(0.087, abs=0.0005)
    assert (t.ci_low, t.ci_high) == pytest.approx((-0.0006, 0.0091), abs=0.00005)


def test_doc_relative_lift(doc_example):
    c0, i0, c1, i1 = doc_example
    r0, v0 = ratio_delta_var(c0, i0)
    r1, v1 = ratio_delta_var(c1, i1)
    lift = relative_lift_ci(r0, v0, r1, v1)
    assert lift.lift == pytest.approx(0.042, abs=0.0005)
    assert (lift.ci_low, lift.ci_high) == pytest.approx((-0.007, 0.092), abs=0.0005)


def test_reduces_to_welch_when_denominator_is_one():
    # 분모가 모두 1이면 비율 지표는 그냥 유저 평균이고, delta SE는 Welch t 검정의 SE와 같아진다
    rng = np.random.default_rng(3)
    x0 = rng.exponential(30, size=800)
    x1 = rng.exponential(32, size=1_200)
    t = ratio_ztest(x0, np.ones_like(x0), x1, np.ones_like(x1))
    assert t.z == pytest.approx(ttest_ind(x1, x0, equal_var=False).statistic)


def test_matches_linearization_and_bootstrap(doc_example):
    c0, i0, _, _ = doc_example
    r, v = ratio_delta_var(c0, i0)
    # 선형화: 유저마다 (클릭 - R × 노출) / 평균 노출 을 만들어 평균의 분산을 구하면 같은 값
    lin = (c0 - r * i0) / i0.mean()
    assert v == pytest.approx(lin.var(ddof=1) / len(lin))
    # 유저를 단위로 다시 뽑는 부트스트랩과도 5% 안에서 맞는다
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(c0), size=(2_000, len(c0)))
    boot = c0[idx].sum(axis=1) / i0[idx].sum(axis=1)
    assert np.sqrt(v) == pytest.approx(boot.std(ddof=1), rel=0.05)


def test_relative_lift_matches_bootstrap(doc_example):
    c0, i0, c1, i1 = doc_example
    r0, v0 = ratio_delta_var(c0, i0)
    r1, v1 = ratio_delta_var(c1, i1)
    rng = np.random.default_rng(1)
    n = len(c0)
    a = rng.integers(0, n, size=(2_000, n))
    b = rng.integers(0, n, size=(2_000, n))
    boot = (c1[b].sum(1) / i1[b].sum(1)) / (c0[a].sum(1) / i0[a].sum(1)) - 1
    assert relative_lift_ci(r0, v0, r1, v1).se == pytest.approx(boot.std(ddof=1), rel=0.05)


def test_aa_false_positive_rate():
    # 문서 판단 기준 1절 그림: A/A에서 노출 단위 계산은 5%를 크게 넘고 delta는 5% 근처
    rng = np.random.default_rng(11)
    naive = delta = 0
    sims = 500
    for _ in range(sims):
        c0, i0 = simulate_users(rng, 2_000)
        c1, i1 = simulate_users(rng, 2_000)
        naive += two_proportion_ztest(c0.sum(), i0.sum(), c1.sum(), i1.sum(), pooled=False)[1] < 0.05
        delta += ratio_ztest(c0, i0, c1, i1).p_value < 0.05
    assert naive / sims > 0.09
    assert 0.025 <= delta / sims <= 0.08


@pytest.mark.parametrize("m,expected", [(1, 1.00), (10, 1.29), (50, 2.14)])
def test_se_inflation_table(m, expected):
    # 문서 판단 기준 3절 표: 유저당 노출이 많을수록 노출 단위 SE가 더 작게 나온다
    clk, imp = simulate_users(np.random.default_rng(1), 40_000, mean_impressions=m)
    r, v = ratio_delta_var(clk, imp)
    assert np.sqrt(v / (r * (1 - r) / imp.sum())) == pytest.approx(expected, abs=0.005)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        ratio_delta_var([1, 2, 3], [1, 2])
    with pytest.raises(ValueError):
        ratio_delta_var([1], [1])
    with pytest.raises(ValueError):
        ratio_delta_var([0, 0], [0, 0])
    with pytest.raises(ValueError):
        relative_lift_ci(0, 0.1, 0.2, 0.1)
