import numpy as np
import pandas as pd
import pytest

from causal_inference.psm import smd, propensity_scores, match_nearest, balance_table, psm_att

TRUE_EFFECT = 2.0


def make_selection_data(seed=0, n=4000):
    """x가 클수록 처치를 더 받고 결과도 높다. 단순 비교는 위로 치우친다."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    p = 1 / (1 + np.exp(-(-1.0 + 1.5 * x)))
    treat = (rng.uniform(size=n) < p).astype(int)
    y = TRUE_EFFECT * treat + 3.0 * x + rng.normal(0, 1, n)
    return pd.DataFrame({"x": x, "treat": treat, "y": y})


def test_smd_known_values():
    a = pd.Series([0.0, 2.0, 4.0])
    assert smd(a, a) == 0.0
    # 평균 차 2, 두 집단 분산 모두 4 -> SMD = 2 / 2 = 1
    assert smd(a + 2, a) == pytest.approx(1.0)


def test_propensity_scores_track_true_probability():
    df = make_selection_data()
    ps = propensity_scores(df, "treat", ["x"])
    true_p = 1 / (1 + np.exp(-(-1.0 + 1.5 * df["x"])))
    assert np.abs(ps - true_p).max() < 0.05


def test_match_nearest_picks_closest():
    idx = match_nearest([0.21, 0.79], [0.1, 0.2, 0.5, 0.8])
    assert list(idx) == [1, 3]


def test_psm_recovers_effect_where_naive_fails():
    df = make_selection_data()
    naive = df.loc[df.treat == 1, "y"].mean() - df.loc[df.treat == 0, "y"].mean()
    att, treated, control, matched = psm_att(df, "treat", "y", ["x"])
    assert naive > TRUE_EFFECT + 2
    assert att == pytest.approx(TRUE_EFFECT, abs=0.3)

    balance = balance_table(treated, control, matched, ["x"])
    assert abs(balance["smd_before"].iloc[0]) > 0.5
    assert abs(balance["smd_after"].iloc[0]) < 0.1
