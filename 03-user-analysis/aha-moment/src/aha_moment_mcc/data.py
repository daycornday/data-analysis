"""합성 유저 데이터: 숨은 관여도 z가 행동 횟수와 잔존을 둘 다 만든다."""
import numpy as np
import pandas as pd


def make_users(seed=20261020, n=50_000):
    """유저 n명의 7일 안 핵심 행동 횟수(count)와 4주차 잔존 여부(retained).

    행동과 잔존은 서로를 만들지 않는다. 둘 다 z에서 나온다.
    """
    rng = np.random.default_rng(seed)
    z = rng.normal(size=n)
    mu = np.exp(1.6 + 0.7 * z)
    count = rng.negative_binomial(1.0, 1.0 / (1.0 + mu))
    retained = rng.random(n) < 1 / (1 + np.exp(-(-2.15 + 0.6 * z)))
    return pd.DataFrame({"user_id": np.arange(n), "count": count,
                         "retained": retained.astype(int)})
