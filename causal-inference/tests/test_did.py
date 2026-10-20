import numpy as np
import pandas as pd
import pytest

from causal_inference.did import did_table, did_regression, pre_trend_slopes, event_study

TRUE_EFFECT = -0.03
FIRST_POST = 5


def make_panel(seed=0, n_units=30, n_periods=8, n_treated=10):
    """집단마다 수준이 다르고, 모두 같은 추세를 따르며, 처치군만 5기부터 효과가 생기는 패널."""
    rng = np.random.default_rng(seed)
    rows = []
    for unit in range(n_units):
        level = rng.normal(0.4, 0.05)
        treated = int(unit < n_treated)
        for t in range(1, n_periods + 1):
            effect = TRUE_EFFECT if (treated and t >= FIRST_POST) else 0.0
            y = level + 0.004 * t + effect + rng.normal(0, 0.005)
            rows.append({"unit": unit, "t": t, "treated": treated,
                         "post": int(t >= FIRST_POST), "y": y})
    return pd.DataFrame(rows)


def test_did_table_recovers_effect():
    _, did = did_table(make_panel(), "y", "treated", "post")
    assert did == pytest.approx(TRUE_EFFECT, abs=0.004)


def test_regression_matches_table():
    df = make_panel()
    _, did = did_table(df, "y", "treated", "post")
    fit = did_regression(df, "y", "treated", "post", cluster="unit")
    assert fit.params["treated:post"] == pytest.approx(did, abs=1e-10)
    assert fit.pvalues["treated:post"] < 0.01


def test_pre_trend_slopes_are_common_trend():
    slopes = pre_trend_slopes(make_panel(), "y", "treated", "t", FIRST_POST - 1)
    assert slopes[0] == pytest.approx(0.004, abs=0.002)
    assert slopes[1] == pytest.approx(0.004, abs=0.002)


def test_event_study_flat_before_and_shifted_after():
    es = event_study(make_panel(), "y", "unit", "t", "treated",
                     ref_time=FIRST_POST - 1, cluster="unit")
    assert es.loc[es["k"] == -1, "coef"].iloc[0] == 0.0
    pre = es[es["k"] < -1]["coef"]
    post = es[es["k"] >= 0]["coef"]
    assert (pre.abs() < 0.006).all()
    assert post.mean() == pytest.approx(TRUE_EFFECT, abs=0.004)
