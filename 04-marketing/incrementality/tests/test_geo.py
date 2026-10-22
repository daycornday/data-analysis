from marketing_incrementality import geo


def test_did_recovers_iroas():
    panel = geo.simulate_geo(true_iroas=1.8, seed=21)
    res = geo.did_estimate(panel)
    assert res["iroas_ci"][0] < 1.8 < res["iroas_ci"][1]
    assert abs(res["iroas"] - 1.8) < 0.4


def test_did_recovers_total_increment():
    panel = geo.simulate_geo(true_iroas=1.8, n_regions=80, seed=22)
    res = geo.did_estimate(panel)
    truth = panel["true_lift"].sum()
    assert abs(res["incremental_sales"] / truth - 1) < 0.15


def test_did_zero_effect():
    panel = geo.simulate_geo(true_iroas=0.0, seed=23)
    res = geo.did_estimate(panel)
    assert res["att_ci"][0] < 0 < res["att_ci"][1]


def test_pretrend_flat_when_parallel():
    panel = geo.simulate_geo(seed=24)
    assert geo.pretrend_test(panel)["p_value"] > 0.05


def test_pretrend_detects_diverging_trend():
    panel = geo.simulate_geo(seed=25)
    drift = (panel["treated"] == 1) * panel["week"] * 1.0
    panel = panel.assign(sales=panel["sales"] + drift)
    assert geo.pretrend_test(panel)["p_value"] < 0.05
