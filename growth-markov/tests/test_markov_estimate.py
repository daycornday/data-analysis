import numpy as np

from growth_markov.chain import STATES, true_transition_matrix, simulate_logs
from growth_markov.estimate import estimate_matrix, bootstrap_matrices, normalize_rows


def test_true_matrix_rows_sum_to_one():
    P = true_transition_matrix()
    assert np.allclose(P.sum(axis=1), 1.0)


def test_estimate_recovers_known_matrix():
    P = true_transition_matrix()
    logs = simulate_logs(P, n_months=24, new_per_month=2000, seed=1)
    P_hat = estimate_matrix(logs)
    assert np.allclose(P_hat.sum(axis=1), 1.0)
    assert np.abs(P_hat - P).max() < 0.02


def test_normalize_rows_on_hand_counts():
    counts = np.zeros((len(STATES), len(STATES)))
    counts[0, 1], counts[0, 6] = 3, 1
    P = normalize_rows(counts)
    assert P[0, 1] == 0.75 and P[0, 6] == 0.25
    assert P[6, 6] == 1.0


def test_bootstrap_interval_covers_truth():
    P = true_transition_matrix()
    logs = simulate_logs(P, n_months=12, new_per_month=1000, seed=2)
    boots = bootstrap_matrices(logs, n_boot=100, seed=0)
    lo, hi = np.percentile(boots, [0.5, 99.5], axis=0)
    cells = P[:-1] > 0
    covered = ((lo[:-1] <= P[:-1]) & (P[:-1] <= hi[:-1]))[cells]
    assert covered.mean() >= 0.9
