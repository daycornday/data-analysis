import numpy as np
import pytest

from segmentation_gmm.compose import closure, shares_from_counts, clr, clr_inverse, drop_last


def test_closure_rows_sum_to_one():
    assert np.allclose(closure([[1, 3], [2, 2]]).sum(axis=1), 1.0)


def test_clr_rows_sum_to_zero():
    z = clr(closure(np.random.default_rng(0).random((50, 5)) + 0.01))
    assert np.allclose(z.sum(axis=1), 0.0)


def test_clr_ignores_total_volume():
    # 같은 비율이면 사용량이 10배여도 CLR이 같다
    counts = np.array([[10, 20, 70]])
    assert np.allclose(clr(closure(counts)), clr(closure(counts * 10)))


def test_clr_known_value():
    # (1/4, 1/4, 1/2): 기하평균 = 2^(-5/3), log(1/2) - log(2^(-5/3)) = (2/3) log 2
    z = clr(np.array([[0.25, 0.25, 0.5]]))
    assert z[0, 2] == pytest.approx(2 / 3 * np.log(2))


def test_clr_inverse_roundtrip():
    x = closure(np.array([[1.0, 2.0, 7.0]]))
    assert np.allclose(clr_inverse(clr(x)), x)


def test_zero_counts_are_handled():
    s = shares_from_counts(np.array([[0, 5, 5]]))
    assert (s > 0).all() and np.isfinite(clr(s)).all()


def test_drop_last_shape():
    assert drop_last(np.zeros((3, 5))).shape == (3, 4)
