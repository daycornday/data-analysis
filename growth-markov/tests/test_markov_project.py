import numpy as np
import pytest

from growth_markov.chain import STATES, true_transition_matrix
from growth_markov.project import (
    LEVERS, steady_state, project, active_users, improve, sensitivity,
)


def test_steady_state_is_fixed_point():
    P = true_transition_matrix()
    x = steady_state(P, 1000)
    nxt = project(P, x, 1000, months=1)[-1]
    assert np.allclose(nxt[:-1], x[:-1])


def test_projection_converges_to_steady_state():
    P = true_transition_matrix()
    path = project(P, np.zeros(len(STATES)), 1000, months=200)
    assert np.allclose(path[-1][:-1], steady_state(P, 1000)[:-1], rtol=1e-6)


def test_steady_state_on_two_state_toy():
    # 신규가 매달 100명, 신규는 다음 달 전원 이탈 -> 정상상태 신규 100명
    P = np.zeros((len(STATES), len(STATES)))
    P[:, -1] = 1.0
    assert steady_state(P, 100)[0] == pytest.approx(100)


def test_improve_keeps_rows_stochastic():
    P = true_transition_matrix()
    for src, dst in LEVERS:
        for delta in (0.01, -0.01):
            Q = improve(P, src, dst, delta)
            assert np.allclose(Q.sum(axis=1), 1.0)
            assert (Q >= 0).all()
            i, j = STATES.index(src), STATES.index(dst)
            assert Q[i, j] == pytest.approx(P[i, j] + delta)


def test_every_lever_helps_active_users():
    P = true_transition_matrix()
    gains = sensitivity(P, steady_state(P, 1000), 1000, months=12)
    assert all(g > 0 for g in gains.values())
