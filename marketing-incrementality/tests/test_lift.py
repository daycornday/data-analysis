import numpy as np

from marketing_incrementality import lift


def test_uplift_recovered_within_ci():
    df = lift.simulate_users(true_uplift=0.008, seed=11)
    res = lift.estimate_lift(df)
    lo, hi = res["uplift_ci"]
    assert lo < 0.008 < hi
    assert abs(res["uplift"] - 0.008) < 0.003


def test_iroas_close_to_design_value():
    # 설계상 iROAS = 0.008 x 30,000 / 96 = 2.5
    df = lift.simulate_users(n_users=400000, true_uplift=0.008,
                             mean_order_value=30000, cost_per_user=96.0, seed=12)
    res = lift.estimate_lift(df)
    assert res["iroas_ci"][0] < 2.5 < res["iroas_ci"][1]
    assert abs(res["iroas"] - 2.5) < 0.6


def test_last_click_overstates_increment():
    df = lift.simulate_users(seed=13)
    table = lift.attribution_vs_increment(df, lift.estimate_lift(df))
    last_click, truth = table["매출"].iloc[1], table["매출"].iloc[3]
    assert last_click > 2 * truth


def test_no_effect_gives_zero_increment():
    df = lift.simulate_users(true_uplift=0.0, seed=14)
    res = lift.estimate_lift(df)
    assert res["uplift_ci"][0] < 0 < res["uplift_ci"][1]


def test_diff_in_means_known_values():
    a = np.array([1.0, 1.0, 1.0, 1.0])
    b = np.array([0.0, 0.0, 0.0, 0.0])
    diff, lo, hi = lift.diff_in_means(a, b)
    assert diff == 1.0 and lo == 1.0 and hi == 1.0
