import numpy as np
import pytest

from marketing_incrementality import mmm

TRUE_ROI = {"tv": 1.8, "search": 1.2, "social": 2.5}
TRUE_PARAMS = {"tv": (0.65, 1.2, 2.0), "search": (0.1, 0.5, 1.0), "social": (0.3, 1.6, 2.0)}


def test_adstock_known_values():
    out = mmm.adstock([10, 0, 0, 0], 0.5)
    assert np.allclose(out, [10, 5, 2.5, 1.25])


def test_hill_half_at_k():
    assert mmm.hill(4.0, 4.0, 2.0) == pytest.approx(0.5)
    assert mmm.hill(0.0, 4.0, 2.0) == 0.0


def test_simulated_roi_matches_truth():
    spend = mmm.simulate_spend()
    df, _ = mmm.simulate_sales(spend, TRUE_PARAMS, TRUE_ROI)
    for c in mmm.CHANNELS:
        assert df["contrib_" + c].sum() / spend[c].sum() == pytest.approx(TRUE_ROI[c])


def test_fit_recovers_roi_and_carryover():
    spend = mmm.simulate_spend()
    df, _ = mmm.simulate_sales(spend, TRUE_PARAMS, TRUE_ROI)
    fit = mmm.fit_mmm(df)
    roi = mmm.channel_roi(df, fit).set_index("channel")["roi"]
    assert abs(roi["tv"] / 1.8 - 1) < 0.15
    assert abs(roi["social"] / 2.5 - 1) < 0.15
    assert abs(roi["search"] / 1.2 - 1) < 0.3
    assert abs(fit["params"]["tv"][0] - 0.65) <= 0.15
    assert fit["r2"] > 0.9


def test_response_steady_state():
    # 이월률 0.5면 매주 10씩 쓸 때 adstock은 20, K=20이면 hill = 0.5
    assert mmm.response(10.0, 0.5, 20.0, 1.0, 100.0) == pytest.approx(50.0)


def test_reallocation_keeps_budget_and_finds_saturated_channel():
    spend = mmm.simulate_spend()
    df, betas = mmm.simulate_sales(spend, TRUE_PARAMS, TRUE_ROI)
    curves = {c: (TRUE_PARAMS[c][0], TRUE_PARAMS[c][1] * mmm.adstock(spend[c], TRUE_PARAMS[c][0]).mean(),
                  TRUE_PARAMS[c][2], betas[c]) for c in mmm.CHANNELS}
    budget = {c: spend[c].mean() for c in mmm.CHANNELS}
    marginal = mmm.marginal_roi(budget, curves)
    assert min(marginal, key=marginal.get) == "search"
    new = mmm.reallocate(budget, "search", "social", 0.3)
    assert sum(new.values()) == pytest.approx(sum(budget.values()))
    assert mmm.total_response(new, curves) > mmm.total_response(budget, curves)
