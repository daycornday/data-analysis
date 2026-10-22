"""간단한 MMM (마케팅 믹스 모델).

주간 매출 = 기본 수요(상수, 추세, 계절) + 채널별 beta x hill(adstock(광고비))

adstock 이월률(lam), hill 반포화점(K), hill 모양(shape)은 격자 탐색으로 고르고,
그 값이 정해지면 나머지 계수(beta, 기본 수요)는 최소제곱으로 푼다.
채널을 하나씩 돌아가며 격자를 다시 훑는 좌표 하강을 몇 바퀴 반복한다.
"""
import numpy as np
import pandas as pd
from scipy.signal import lfilter

CHANNELS = ["tv", "search", "social"]
LAM_GRID = np.round(np.arange(0.0, 0.91, 0.1), 2)
K_GRID = np.array([0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
SHAPE_GRID = np.array([1.0, 2.0, 3.0])


def adstock(x, lam):
    """A_t = x_t + lam x A_{t-1}."""
    return lfilter([1.0], [1.0, -lam], np.asarray(x, dtype=float))


def hill(a, k, shape):
    """S(A) = A^s / (A^s + K^s). K에서 0.5가 된다."""
    a = np.asarray(a, dtype=float)
    return a ** shape / (a ** shape + k ** shape)


def transform(x, lam, k_mult, shape):
    """광고비 -> adstock -> hill. K는 adstock 평균의 배수로 둔다."""
    a = adstock(x, lam)
    return hill(a, k_mult * a.mean(), shape)


def simulate_spend(n_weeks=156, correlated=False, seed=3):
    """채널 3개의 주간 광고비 (백만 원).

    correlated=True면 세 채널이 같은 예산 흐름을 따라 같이 늘고 준다.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n_weeks)
    if correlated:
        common = 1 + 0.5 * np.sin(2 * np.pi * t / 52) + rng.normal(0, 0.15, n_weeks)
        return pd.DataFrame({
            "tv": np.clip(40 * common + rng.normal(0, 2, n_weeks), 0, None),
            "search": np.clip(20 * common + rng.normal(0, 1, n_weeks), 0, None),
            "social": np.clip(15 * common + rng.normal(0, 1, n_weeks), 0, None),
        })
    flight = np.repeat(rng.uniform(size=n_weeks // 4 + 1) < 0.5, 4)[:n_weeks]
    return pd.DataFrame({
        "tv": flight * rng.uniform(50, 90, n_weeks),
        "search": rng.uniform(5, 40, n_weeks),
        "social": rng.uniform(0, 30, n_weeks),
    })


def baseline_design(n_weeks):
    """상수, 추세, 1년 주기 사인/코사인 2쌍."""
    t = np.arange(n_weeks)
    cols = [np.ones(n_weeks), t / n_weeks]
    for h in (1, 2):
        cols += [np.sin(2 * np.pi * h * t / 52), np.cos(2 * np.pi * h * t / 52)]
    return np.column_stack(cols)


def simulate_sales(spend, params, true_roi, noise_sd=10.0, seed=4):
    """정답 모수로 주간 매출을 만든다.

    beta는 채널별 평균 ROI(기여 매출 합 / 광고비 합)가 true_roi가 되도록 맞춘다.
    """
    rng = np.random.default_rng(seed)
    n = len(spend)
    t = np.arange(n)
    base = 500 + 60 * t / n + 50 * np.sin(2 * np.pi * t / 52) + 20 * np.cos(2 * np.pi * t / 52)
    contrib = {}
    betas = {}
    for c in CHANNELS:
        s = transform(spend[c].values, *params[c])
        betas[c] = true_roi[c] * spend[c].sum() / s.sum()
        contrib[c] = betas[c] * s
    sales = base + sum(contrib.values()) + rng.normal(0, noise_sd, n)
    df = spend.copy()
    df["sales"] = sales
    df["base"] = base
    for c in CHANNELS:
        df["contrib_" + c] = contrib[c]
    return df, betas


def _ols(x_base, feats, y):
    """최소제곱. 채널 계수가 음수면 광고가 매출을 깎는다는 뜻이라 후보에서 뺀다 (sse=inf)."""
    x = np.column_stack([x_base] + feats)
    coef = np.linalg.solve(x.T @ x, x.T @ y)
    if np.any(coef[x_base.shape[1]:] < 0):
        return coef, np.inf
    sse = np.sum((y - x @ coef) ** 2)
    return coef, sse


def fit_mmm(df, n_rounds=4):
    """격자 탐색 + 최소제곱. 채널별 (lam, K배수, shape)와 beta를 돌려준다."""
    y = df["sales"].values
    x_base = baseline_design(len(df))
    grid = [(l, k, s) for l in LAM_GRID for k in K_GRID for s in SHAPE_GRID]
    cache = {c: {g: transform(df[c].values, *g) for g in grid} for c in CHANNELS}
    chosen = {c: (0.3, 1.0, 1.0) for c in CHANNELS}

    for _ in range(n_rounds):
        for c in CHANNELS:
            best = None
            best = (np.inf, chosen[c])
            for g in grid:
                trial = dict(chosen, **{c: g})
                _, sse = _ols(x_base, [cache[ch][trial[ch]] for ch in CHANNELS], y)
                if sse < best[0]:
                    best = (sse, g)
            chosen[c] = best[1]

    feats = [cache[c][chosen[c]] for c in CHANNELS]
    x = np.column_stack([x_base] + feats)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    sse = np.sum((y - x @ coef) ** 2)
    n_base = x_base.shape[1]
    betas = {c: coef[n_base + i] for i, c in enumerate(CHANNELS)}
    fitted = x_base @ coef[:n_base] + sum(betas[c] * feats[i] for i, c in enumerate(CHANNELS))
    r2 = 1 - sse / np.sum((y - y.mean()) ** 2)
    return {"params": chosen, "betas": betas, "fitted": fitted,
            "base": x_base @ coef[:n_base], "r2": r2,
            "adstock_mean": {c: adstock(df[c].values, chosen[c][0]).mean() for c in CHANNELS}}


def channel_roi(df, fit):
    """채널별 기여 매출 합과 평균 ROI."""
    rows = []
    for c in CHANNELS:
        contrib = fit["betas"][c] * transform(df[c].values, *fit["params"][c])
        rows.append((c, contrib.sum(), df[c].sum(), contrib.sum() / df[c].sum()))
    return pd.DataFrame(rows, columns=["channel", "contribution", "spend", "roi"])


def response(weekly_spend, lam, k_abs, shape, beta):
    """매주 같은 광고비를 계속 쓸 때 주간 기여 매출 (정상 상태).

    정상 상태 adstock = x / (1 - lam).
    """
    a = np.asarray(weekly_spend, dtype=float) / (1 - lam)
    return beta * hill(a, k_abs, shape)


def curve_params(params, betas, adstock_mean):
    """채널별 (lam, K 절대값, shape, beta) 묶음."""
    return {c: (params[c][0], params[c][1] * adstock_mean[c], params[c][2], betas[c])
            for c in CHANNELS}


def total_response(budget, curves):
    """채널별 주간 광고비 dict -> 주간 광고 기여 매출 합."""
    return sum(float(response(budget[c], *curves[c])) for c in CHANNELS)


def marginal_roi(budget, curves, step=1.0):
    """현재 광고비에서 1 더 쓸 때 늘어나는 매출 (채널별)."""
    out = {}
    for c in CHANNELS:
        up = dict(budget, **{c: budget[c] + step})
        out[c] = (total_response(up, curves) - total_response(budget, curves)) / step
    return out


def reallocate(budget, src, dst, share):
    """src 채널 예산의 share만큼을 dst로 옮긴 새 예산."""
    moved = budget[src] * share
    new = dict(budget)
    new[src] -= moved
    new[dst] += moved
    return new
