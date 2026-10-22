"""상태 로그에서 전이행렬 추정 (카운트 후 행 정규화), 유저 단위 부트스트랩."""
import numpy as np

from .chain import STATES, CHURNED


def transition_pairs(logs):
    """같은 유저의 연속한 두 달을 (이번 달 상태 번호, 다음 달 상태 번호, user_id)로 뽑는다."""
    df = logs.sort_values(["user_id", "month"])
    code = df["state"].map({s: i for i, s in enumerate(STATES)}).to_numpy()
    user = df["user_id"].to_numpy()
    month = df["month"].to_numpy()
    consecutive = (user[1:] == user[:-1]) & (month[1:] == month[:-1] + 1)
    return code[:-1][consecutive], code[1:][consecutive], user[:-1][consecutive]


def count_matrix(src, dst, weights=None):
    k = len(STATES)
    flat = np.bincount(src * k + dst, weights=weights, minlength=k * k)
    return flat.reshape(k, k)


def normalize_rows(counts):
    """카운트를 행 합으로 나눈다. 이탈은 정의상 흡수 상태로 고정한다."""
    P = counts / counts.sum(axis=1, keepdims=True).clip(min=1e-12)
    P[CHURNED] = 0.0
    P[CHURNED, CHURNED] = 1.0
    return P


def estimate_matrix(logs):
    src, dst, _ = transition_pairs(logs)
    return normalize_rows(count_matrix(src, dst))


def bootstrap_matrices(logs, n_boot=200, seed=0):
    """유저를 복원추출해 전이행렬을 n_boot번 다시 추정한다. 같은 유저의 전이는 묶어서 뽑힌다."""
    rng = np.random.default_rng(seed)
    src, dst, user = transition_pairs(logs)
    users, user_idx = np.unique(user, return_inverse=True)
    mats = []
    for _ in range(n_boot):
        draw = rng.integers(0, len(users), len(users))
        times_drawn = np.bincount(draw, minlength=len(users))
        mats.append(normalize_rows(count_matrix(src, dst, weights=times_drawn[user_idx])))
    return np.array(mats)
