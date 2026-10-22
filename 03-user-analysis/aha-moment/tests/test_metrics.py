import numpy as np

from aha_moment_mcc import (
    make_users, confusion, aha_ratio, mcc, sweep_thresholds, plateau,
)


def test_confusion_counts_four_cells():
    pred = [1, 1, 0, 0, 1]
    actual = [1, 0, 1, 0, 1]
    assert confusion(pred, actual) == (2, 1, 1, 1)


def test_aha_ratio_is_jaccard_of_two_sets():
    pred = np.array([1, 1, 1, 0, 0, 0, 1, 0])
    actual = np.array([1, 0, 1, 1, 0, 0, 0, 0])
    a, b = set(np.where(pred)[0]), set(np.where(actual)[0])
    jaccard = len(a & b) / len(a | b)
    assert abs(aha_ratio(*confusion(pred, actual)) - jaccard) < 1e-12


def test_aha_ratio_all_positive_equals_base_rate():
    rng = np.random.default_rng(0)
    actual = rng.random(1000) < 0.12
    pred = np.ones(1000, dtype=bool)
    assert abs(aha_ratio(*confusion(pred, actual)) - actual.mean()) < 1e-12


def test_mcc_equals_pearson_of_binary_vectors():
    rng = np.random.default_rng(1)
    actual = rng.random(5000) < 0.2
    pred = (actual & (rng.random(5000) < 0.6)) | (rng.random(5000) < 0.1)
    r = np.corrcoef(pred.astype(int), actual.astype(int))[0, 1]
    assert abs(mcc(*confusion(pred, actual)) - r) < 1e-12


def test_mcc_known_values():
    assert mcc(10, 0, 0, 10) == 1.0
    assert mcc(0, 10, 10, 0) == -1.0
    assert mcc(0, 0, 5, 95) == 0.0  # 예측 양성 0명이면 정의상 0


def test_mcc_independent_predictor_near_zero():
    rng = np.random.default_rng(2)
    actual = rng.random(200_000) < 0.12
    pred = rng.random(200_000) < 0.5
    assert abs(mcc(*confusion(pred, actual))) < 0.01


def test_synthetic_data_matches_readme():
    df = make_users(20261020)
    assert len(df) == 50_000
    assert int(df["retained"].sum()) == 5869


def test_sweep_picks_differ_on_synthetic_data():
    df = make_users(20261020)
    table = sweep_thresholds(df["count"], df["retained"], range(1, 31))
    row = table.set_index("N").loc[12]
    assert (row.tp, row.fp, row.fn, row.tn) == (1391, 6438, 4478, 37693)
    assert int(table.loc[table["aha_ratio"].idxmax(), "N"]) == 6
    assert int(table.loc[table["mcc"].idxmax(), "N"]) == 12


def test_plateau_threshold_share():
    import pandas as pd
    t = pd.DataFrame({"N": [1, 2, 3, 4], "mcc": [0.5, 0.96, 1.0, 0.94]})
    assert plateau(t, "mcc", 0.95) == [2, 3]
