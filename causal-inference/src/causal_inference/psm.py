"""성향점수 매칭(PSM) 계산 함수."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.neighbors import NearestNeighbors


def propensity_scores(df, treat, covariates):
    """로지스틱 회귀로 P(처치 = 1 | 공변량)을 추정한다."""
    X = sm.add_constant(df[covariates].astype(float))
    model = sm.Logit(df[treat], X).fit(disp=0, maxiter=200)
    return pd.Series(model.predict(X), index=df.index)


def match_nearest(treated_ps, control_ps):
    """처치군마다 성향점수가 가장 가까운 대조군 1명을 고른다 (1:1, 복원 매칭).

    돌려주는 값은 control_ps 안의 위치(0부터) 배열이다.
    """
    nn = NearestNeighbors(n_neighbors=1).fit(np.asarray(control_ps).reshape(-1, 1))
    _, idx = nn.kneighbors(np.asarray(treated_ps).reshape(-1, 1))
    return idx.flatten()


def smd(treated_values, control_values):
    """표준화 평균 차이: (처치 평균 - 대조 평균) / sqrt((분산 합) / 2)."""
    diff = treated_values.mean() - control_values.mean()
    pooled_sd = np.sqrt((treated_values.var() + control_values.var()) / 2)
    return diff / pooled_sd


def balance_table(treated, control, matched_control, covariates):
    """공변량마다 매칭 전, 매칭 후 SMD를 나란히 보여 준다."""
    rows = []
    for col in covariates:
        rows.append({
            "covariate": col,
            "smd_before": smd(treated[col], control[col]),
            "smd_after": smd(treated[col], matched_control[col]),
        })
    return pd.DataFrame(rows)


def psm_att(df, treat, outcome, covariates):
    """성향점수 추정, 1:1 최근접 매칭, ATT 계산을 한 번에 한다.

    돌려주는 값: ATT, 처치군, 전체 대조군, 매칭된 대조군 (성향점수 열 'ps' 포함).
    """
    data = df.copy()
    data["ps"] = propensity_scores(data, treat, covariates)
    treated = data[data[treat] == 1]
    control = data[data[treat] == 0]
    idx = match_nearest(treated["ps"], control["ps"])
    matched = control.iloc[idx]
    att = treated[outcome].mean() - matched[outcome].mean()
    return att, treated, control, matched
