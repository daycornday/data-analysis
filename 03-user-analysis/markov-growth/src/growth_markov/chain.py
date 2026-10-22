"""유저 상태 정의, 정답 전이행렬, 합성 월별 상태 로그 생성."""
import numpy as np
import pandas as pd

STATES = ["new", "first_month", "active", "at_risk", "dormant", "returned", "churned"]
LABELS = ["신규", "첫 달 활성", "활성", "이탈 위험", "휴면", "복귀", "이탈"]
ACTIVE_STATES = ["first_month", "active", "returned"]
CHURNED = STATES.index("churned")
NEW = STATES.index("new")


def true_transition_matrix():
    """합성 데이터를 만드는 정답 월간 전이행렬. 행 = 이번 달 상태, 열 = 다음 달 상태."""
    rows = {
        "new":         {"first_month": 0.55, "dormant": 0.30, "churned": 0.15},
        "first_month": {"active": 0.50, "at_risk": 0.25, "dormant": 0.15, "churned": 0.10},
        "active":      {"active": 0.80, "at_risk": 0.15, "dormant": 0.04, "churned": 0.01},
        "at_risk":     {"active": 0.35, "at_risk": 0.20, "dormant": 0.35, "churned": 0.10},
        "dormant":     {"dormant": 0.65, "returned": 0.10, "churned": 0.25},
        "returned":    {"active": 0.45, "at_risk": 0.25, "dormant": 0.25, "churned": 0.05},
        "churned":     {"churned": 1.0},
    }
    P = np.zeros((len(STATES), len(STATES)))
    for src, dests in rows.items():
        for dst, p in dests.items():
            P[STATES.index(src), STATES.index(dst)] = p
    return P


def simulate_logs(P, n_months=24, new_per_month=2000, seed=0):
    """매달 new_per_month명이 '신규'로 들어오고 P를 따라 움직이는 월별 상태 로그.

    한 행 = (user_id, month, state). 이탈 상태에 들어간 달까지 기록하고 그 뒤는 남기지 않는다.
    """
    rng = np.random.default_rng(seed)
    cum = P.cumsum(axis=1)
    cum[:, -1] = 1.0  # 부동소수 오차로 1을 살짝 밑도는 경우 막기
    records = []
    user_id = 0
    for start in range(n_months):
        ids = np.arange(user_id, user_id + new_per_month)
        user_id += new_per_month
        state = np.full(new_per_month, NEW)
        alive = np.ones(new_per_month, dtype=bool)
        for month in range(start, n_months):
            records.append(pd.DataFrame({"user_id": ids[alive], "month": month, "state": state[alive]}))
            alive &= state != CHURNED
            u = rng.random(new_per_month)
            state = (u[:, None] > cum[state]).sum(axis=1)
    logs = pd.concat(records, ignore_index=True)
    logs["state"] = logs["state"].map(dict(enumerate(STATES)))
    return logs.sort_values(["user_id", "month"]).reset_index(drop=True)
