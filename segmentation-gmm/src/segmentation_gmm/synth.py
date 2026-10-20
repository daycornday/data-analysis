"""정답 세그먼트를 심은 합성 기능 사용 데이터."""
import numpy as np
import pandas as pd

FEATURES = ["편집", "검색", "공유", "내보내기", "협업"]

# 세그먼트별 평균 사용 비중. 1번과 2번은 큰 비중이 비슷하고 작은 비중(협업)에서만 갈린다.
SEGMENTS = {
    "편집 집중": {"share": [0.60, 0.20, 0.08, 0.10, 0.02], "size": 0.35, "conversion": 0.06},
    "편집 + 협업": {"share": [0.55, 0.17, 0.07, 0.10, 0.11], "size": 0.15, "conversion": 0.14},
    "탐색형": {"share": [0.25, 0.45, 0.10, 0.15, 0.05], "size": 0.30, "conversion": 0.03},
    "공유, 내보내기형": {"share": [0.30, 0.15, 0.25, 0.27, 0.03], "size": 0.20, "conversion": 0.09},
}


def make_users(n_users=6000, log_sd=0.35, mean_events=500, seed=0):
    """유저별 기능 사용 횟수를 만들고 비중, 정답 세그먼트, 유료 전환 여부를 붙인다.

    비중 = softmax(log(세그먼트 평균 비중) + 정규 잡음). 횟수 = 그 비중의 다항분포.
    """
    rng = np.random.default_rng(seed)
    names = list(SEGMENTS)
    sizes = np.array([SEGMENTS[s]["size"] for s in names])
    seg = rng.choice(len(names), size=n_users, p=sizes / sizes.sum())
    log_mean = np.log(np.array([SEGMENTS[s]["share"] for s in names]))
    logits = log_mean[seg] + rng.normal(0, log_sd, (n_users, len(FEATURES)))
    p = np.exp(logits)
    p /= p.sum(axis=1, keepdims=True)
    totals = np.maximum(rng.poisson(mean_events, n_users), 5)
    counts = np.array([rng.multinomial(t, row) for t, row in zip(totals, p)])
    conv_rate = np.array([SEGMENTS[s]["conversion"] for s in names])[seg]
    df = pd.DataFrame(counts, columns=FEATURES)
    df.insert(0, "user_id", np.arange(n_users))
    df["true_segment"] = np.array(names)[seg]
    df["converted"] = (rng.random(n_users) < conv_rate).astype(int)
    return df
