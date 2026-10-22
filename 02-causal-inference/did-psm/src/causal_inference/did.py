"""이중차분법(DID) 계산 함수."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def did_table(df, outcome, treated, post):
    """2x2 평균표와 DID 값을 돌려준다.

    행은 대조군(0), 처치군(1), 열은 처치 전(0), 처치 후(1)다.
    """
    table = df.groupby([treated, post])[outcome].mean().unstack(post)
    table.columns = ["before", "after"]
    table["change"] = table["after"] - table["before"]
    did = table.loc[1, "change"] - table.loc[0, "change"]
    return table, did


def did_regression(df, outcome, treated, post, cluster):
    """Y ~ treated + post + treated:post 를 집단 단위 클러스터 표준오차로 적합한다."""
    formula = "{y} ~ {t} + {p} + {t}:{p}".format(y=outcome, t=treated, p=post)
    return smf.ols(formula, data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df[cluster]}
    )


def pre_trend_slopes(df, outcome, treated, time, last_pre):
    """처치 전 기간의 집단 평균에 직선을 맞춰 기간당 기울기를 구한다."""
    pre = df[df[time] <= last_pre]
    means = pre.groupby([treated, time])[outcome].mean()
    slopes = {}
    for group in (0, 1):
        series = means.loc[group]
        slopes[group] = np.polyfit(series.index.values, series.values, 1)[0]
    return slopes


def event_study(df, outcome, unit, time, treated, ref_time, cluster):
    """기간별 처치군-대조군 차이(delta_k)를 집단, 기간 고정효과 회귀로 추정한다.

    ref_time(보통 처치 직전 기간)은 기준이라 0으로 둔다.
    돌려주는 표의 k는 ref_time 기준 상대 기간이다(ref_time은 k = -1).
    """
    data = df.copy()
    times = sorted(data[time].unique())
    names = []
    for t in times:
        if t == ref_time:
            continue
        name = "lead_lag_{}".format(t)
        data[name] = ((data[time] == t) & (data[treated] == 1)).astype(int)
        names.append(name)

    formula = "{y} ~ C({u}) + C({tm}) + {terms}".format(
        y=outcome, u=unit, tm=time, terms=" + ".join(names)
    )
    fit = smf.ols(formula, data=data).fit(
        cov_type="cluster", cov_kwds={"groups": data[cluster]}
    )
    ci = fit.conf_int()

    rows = []
    for t in times:
        k = t - ref_time - 1
        if t == ref_time:
            rows.append({"time": t, "k": k, "coef": 0.0, "ci_low": 0.0, "ci_high": 0.0})
            continue
        name = "lead_lag_{}".format(t)
        rows.append({
            "time": t,
            "k": k,
            "coef": fit.params[name],
            "ci_low": ci.loc[name, 0],
            "ci_high": ci.loc[name, 1],
        })
    return pd.DataFrame(rows)
