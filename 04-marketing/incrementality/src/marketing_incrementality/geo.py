"""지역(geo) 실험과 이중차분(DID).

유저 단위로 노출을 막을 수 없는 광고(TV 등)는 지역을 무작위로 나눠
한쪽에만 광고를 켠다. 광고 전후의 지역 매출 변화 차이로 효과를 잰다.
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def simulate_geo(n_regions=40, n_pre=20, n_post=8, true_iroas=1.8,
                 spend_share=0.04, noise_sd=0.03, seed=2):
    """지역 x 주 매출 패널. 단위는 백만 원.

    - 지역 규모는 제각각, 모든 지역이 같은 크기의 계절 흐름(백만 원)을 탄다
    - 지역마다 주별 잡음이 따로 붙는다
    - 처치 지역은 사후 기간에 지역 규모의 spend_share만큼 광고비를 쓰고,
      광고비 x true_iroas 만큼 매출이 늘어난다 (정답)
    """
    rng = np.random.default_rng(seed)
    level = rng.lognormal(np.log(100), 0.4, size=n_regions)
    treated = np.zeros(n_regions, dtype=int)
    treated[rng.permutation(n_regions)[: n_regions // 2]] = 1

    weeks = np.arange(n_pre + n_post)
    season = 8 * np.sin(2 * np.pi * weeks / 52) + 0.2 * weeks
    rows = []
    for r in range(n_regions):
        shock = rng.normal(0, noise_sd, size=len(weeks))
        for w in weeks:
            post = int(w >= n_pre)
            spend = level[r] * spend_share * treated[r] * post
            base = level[r] * (1 + shock[w]) + season[w]
            rows.append((r, w, treated[r], post, spend, base, spend * true_iroas))
    df = pd.DataFrame(rows, columns=["region", "week", "treated", "post",
                                     "spend", "base_sales", "true_lift"])
    df["sales"] = df["base_sales"] + df["true_lift"]
    return df


def did_estimate(df):
    """지역, 주 고정효과 회귀로 처치 효과(지역-주당 증분 매출)를 추정한다.

    sales = 지역 효과 + 주 효과 + tau x (처치 지역 x 사후)
    표준오차는 지역 단위로 묶는다 (같은 지역의 주들은 서로 독립이 아니다).
    """
    d = df.assign(treat_post=df["treated"] * df["post"])
    model = smf.ols("sales ~ C(region) + C(week) + treat_post", data=d).fit(
        cov_type="cluster", cov_kwds={"groups": d["region"]})
    tau = model.params["treat_post"]
    lo, hi = model.conf_int().loc["treat_post"]
    n_cells = d["treat_post"].sum()
    spend = d["spend"].sum()
    return {
        "att": tau,
        "att_ci": (lo, hi),
        "incremental_sales": tau * n_cells,
        "incremental_sales_ci": (lo * n_cells, hi * n_cells),
        "spend": spend,
        "iroas": tau * n_cells / spend,
        "iroas_ci": (lo * n_cells / spend, hi * n_cells / spend),
        "p_value": model.pvalues["treat_post"],
    }


def weekly_means(df):
    """주별 처치, 통제 지역 평균 매출과 그 차이."""
    m = df.pivot_table(index="week", columns="treated", values="sales", aggfunc="mean")
    m.columns = ["control", "treated"]
    m["gap"] = m["treated"] - m["control"]
    return m


def pretrend_test(df):
    """사전 기간 동안 처치-통제 차이에 기울기가 있는지 본다.

    기울기가 0과 다르지 않으면 '나란히 움직였다'는 가정을 버릴 근거가 없다.
    """
    pre = weekly_means(df[df["post"] == 0]).reset_index()
    fit = smf.ols("gap ~ week", data=pre).fit()
    return {"slope": fit.params["week"], "p_value": fit.pvalues["week"]}
