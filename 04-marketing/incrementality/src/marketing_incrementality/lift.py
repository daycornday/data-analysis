"""유저 단위 홀드아웃 리프트 테스트.

광고를 보여 줄 수 있었던 유저를 무작위로 노출 그룹과 홀드아웃으로 나누고,
두 그룹의 구매율, 유저당 매출 차이로 증분을 잰다.
합성 데이터는 유저마다 '광고가 없을 때'와 '있을 때'의 결과를 둘 다 만들어 두므로
진짜 증분(정답)을 알 수 있다.
"""
import numpy as np
import pandas as pd
from scipy import stats


def simulate_users(n_users=200000, holdout_share=0.2, base_rate=0.04,
                   true_uplift=0.008, mean_order_value=30000,
                   cost_per_user=96.0, click_share_organic=0.6,
                   click_share_incremental=0.95, seed=1):
    """유저별 잠재 결과(광고 없음 y0, 광고 있음 y1)를 만든다.

    - 구매 의향은 유저마다 다르다 (평균 base_rate)
    - 광고는 모든 유저의 구매 확률을 true_uplift만큼 올린다
    - 노출 그룹 구매자 중 원래 살 사람도 click_share_organic 비율로 광고를
      마지막에 클릭한다 (리타겟팅에서 흔한 장면). 이 구매도 기여로 잡힌다
    """
    rng = np.random.default_rng(seed)
    intent = rng.gamma(shape=2.0, scale=0.5, size=n_users)
    p0 = np.clip(base_rate * intent, 0, 0.9)
    u = rng.uniform(size=n_users)
    y0 = (u < p0).astype(int)
    y1 = (u < p0 + true_uplift).astype(int)

    treated = (rng.uniform(size=n_users) >= holdout_share).astype(int)
    converted = np.where(treated == 1, y1, y0)
    order_value = rng.lognormal(np.log(mean_order_value) - 0.18, 0.6, size=n_users)

    incremental = (y1 - y0) == 1
    click_prob = np.where(incremental, click_share_incremental, click_share_organic)
    last_click_ad = (treated == 1) & (converted == 1) & (rng.uniform(size=n_users) < click_prob)

    return pd.DataFrame({
        "treated": treated,
        "converted": converted,
        "revenue": converted * order_value,
        "last_click_ad": last_click_ad.astype(int),
        "true_incremental": incremental.astype(int) * treated,
        "true_incremental_revenue": incremental * treated * order_value,
        "cost": treated * cost_per_user,
    })


def diff_in_means(x_t, x_h, alpha=0.05):
    """두 그룹 평균 차이와 Welch 정규 근사 신뢰구간."""
    diff = x_t.mean() - x_h.mean()
    se = np.sqrt(x_t.var(ddof=1) / len(x_t) + x_h.var(ddof=1) / len(x_h))
    z = stats.norm.ppf(1 - alpha / 2)
    return diff, diff - z * se, diff + z * se


def estimate_lift(df, alpha=0.05):
    """증분 구매 수, 증분 매출, iROAS와 신뢰구간을 계산한다.

    노출 그룹 전체로 키운다: 증분 = (유저당 차이) x 노출 유저 수.
    """
    t = df[df["treated"] == 1]
    h = df[df["treated"] == 0]
    n_t = len(t)
    cost = t["cost"].sum()

    rate_diff, rate_lo, rate_hi = diff_in_means(t["converted"], h["converted"], alpha)
    rev_diff, rev_lo, rev_hi = diff_in_means(t["revenue"], h["revenue"], alpha)
    return {
        "n_treated": n_t,
        "n_holdout": len(h),
        "rate_treated": t["converted"].mean(),
        "rate_holdout": h["converted"].mean(),
        "uplift": rate_diff,
        "uplift_ci": (rate_lo, rate_hi),
        "incremental_conversions": rate_diff * n_t,
        "incremental_revenue": rev_diff * n_t,
        "incremental_revenue_ci": (rev_lo * n_t, rev_hi * n_t),
        "cost": cost,
        "iroas": rev_diff * n_t / cost,
        "iroas_ci": (rev_lo * n_t / cost, rev_hi * n_t / cost),
    }


def attribution_vs_increment(df, lift):
    """같은 캠페인을 기여, 증분 두 방식으로 잰 매출과 ROAS 표."""
    t = df[df["treated"] == 1]
    cost = lift["cost"]
    rows = [
        ("노출 그룹 전체 매출 (광고 몫으로 다 잡을 때)", t["revenue"].sum()),
        ("마지막 클릭 기여 매출 (매체 리포트)", t.loc[t["last_click_ad"] == 1, "revenue"].sum()),
        ("증분 매출 추정 (홀드아웃 비교)", lift["incremental_revenue"]),
        ("증분 매출 정답 (합성 데이터)", t["true_incremental_revenue"].sum()),
    ]
    out = pd.DataFrame(rows, columns=["기준", "매출"])
    out["ROAS"] = out["매출"] / cost
    return out
