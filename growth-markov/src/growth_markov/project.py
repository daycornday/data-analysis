"""정상상태, 12개월 투영, 전이 하나를 +1%p 개선했을 때의 민감도."""
import numpy as np

from .chain import STATES, ACTIVE_STATES, CHURNED, NEW

ACTIVE_IDX = [STATES.index(s) for s in ACTIVE_STATES]
TRANSIENT = [i for i in range(len(STATES)) if i != CHURNED]

# 개선 후보: (출발 상태, 도착 상태). 늘린 확률만큼 같은 행의 가장 나쁜 도착지에서 덜어낸다.
LEVERS = [
    ("new", "first_month"),
    ("first_month", "active"),
    ("active", "active"),
    ("at_risk", "active"),
    ("dormant", "returned"),
    ("returned", "active"),
]
# 나쁜 순서. 앞에서부터 덜어낼 확률이 남아 있는 곳을 고른다.
DONOR_ORDER = ["churned", "dormant", "at_risk"]


def inflow_vector(new_per_month):
    a = np.zeros(len(STATES))
    a[NEW] = new_per_month
    return a


def steady_state(P, new_per_month):
    """매달 같은 수의 신규가 들어올 때 이탈을 뺀 상태별 인원이 수렴하는 값.

    x = x Q + a  →  x = a (I - Q)^-1  (Q = 이탈을 뺀 부분행렬)
    """
    Q = P[np.ix_(TRANSIENT, TRANSIENT)]
    a = inflow_vector(new_per_month)[TRANSIENT]
    x = np.zeros(len(STATES))
    x[TRANSIENT] = np.linalg.solve((np.eye(len(TRANSIENT)) - Q).T, a)
    return x


def project(P, x0, new_per_month, months=12):
    """x_{t+1} = x_t P + a 를 months번 반복. 반환 shape = (months + 1, 상태 수)."""
    a = inflow_vector(new_per_month)
    path = [np.asarray(x0, dtype=float)]
    for _ in range(months):
        path.append(path[-1] @ P + a)
    return np.array(path)


def active_users(x):
    return np.asarray(x)[..., ACTIVE_IDX].sum(axis=-1)


def improve(P, src, dst, delta=0.01):
    """P[src, dst]를 delta만큼 올리고 같은 행의 가장 나쁜 도착지에서 그만큼 뺀다.

    delta가 음수면 반대로 악화: P[src, dst]에서 덜어 가장 나쁜 도착지로 보낸다.
    """
    i, j = STATES.index(src), STATES.index(dst)
    if delta < 0 and P[i, j] < -delta:
        raise ValueError("줄일 확률이 부족하다: {} -> {}".format(src, dst))
    for donor in DONOR_ORDER:
        d = STATES.index(donor)
        if d != j and (P[i, d] >= delta or delta < 0) and P[i, d] > 0:
            Q = P.copy()
            Q[i, j] += delta
            Q[i, d] -= delta
            return Q
    raise ValueError("덜어낼 확률이 있는 도착지가 없다: {} -> {}".format(src, dst))


def sensitivity(P, x0, new_per_month, months=12, delta=0.01):
    """레버마다 months 뒤 활성 유저가 기준선보다 몇 명 느는지."""
    base = active_users(project(P, x0, new_per_month, months)[-1])
    gains = {}
    for src, dst in LEVERS:
        improved = project(improve(P, src, dst, delta), x0, new_per_month, months)[-1]
        gains[(src, dst)] = active_users(improved) - base
    return gains
