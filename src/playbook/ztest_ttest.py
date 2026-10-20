"""두 그룹 비교의 z 검정과 t 검정.

문서 docs/methods/z-vs-t.md 의 식을 그대로 코드로 옮겼다.
두 검정의 통계량은 모양이 같다.

    통계량 = (실험군 평균 - 대조군 평균) / SE

다른 것은 둘뿐이다. SE를 무엇으로 계산하나, 통계량을 어떤 분포(정규, t)에 대 보나.
"""
from math import sqrt

from scipy.stats import norm, t


def critical_value(alpha=0.05, df=None, two_sided=True):
    """판정선. df가 없으면 정규분포(z), 있으면 t분포 기준."""
    q = 1 - alpha / 2 if two_sided else 1 - alpha
    return float(norm.ppf(q)) if df is None else float(t.ppf(q, df))


def two_proportion_ztest(x0, n0, x1, n1, pooled=True, two_sided=True):
    """두 비율 z 검정. (z, p값)을 돌려준다.

    x0, n0 : 대조군 전환 수, 표본 수
    x1, n1 : 실험군 전환 수, 표본 수
    pooled : 검정은 "차이 없다"가 전제라서 두 그룹을 합친 비율로 SE를 잡는 게 교과서 방식이다.
             신뢰구간은 각 그룹 비율로 잡는다(pooled=False).
    """
    if min(n0, n1) <= 0 or not (0 <= x0 <= n0 and 0 <= x1 <= n1):
        raise ValueError("전환 수는 0 이상 표본 수 이하, 표본 수는 양수여야 한다")
    p0, p1 = x0 / n0, x1 / n1
    if pooled:
        p = (x0 + x1) / (n0 + n1)
        se = sqrt(p * (1 - p) * (1 / n0 + 1 / n1))
    else:
        se = sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)
    if se == 0:
        raise ValueError("두 그룹 모두 전환이 0이거나 전부라서 SE가 0이다")
    z = (p1 - p0) / se
    p_value = 2 * norm.sf(abs(z)) if two_sided else norm.sf(z)
    return float(z), float(p_value)


def welch_ttest(mean0, sd0, n0, mean1, sd1, n1, two_sided=True):
    """요약 통계로 하는 Welch t 검정. (t, 자유도, p값)을 돌려준다.

    두 그룹 분산이 같다고 가정하지 않는다. 같을 때도 손해가 거의 없어서 연속형 지표의 기본값으로 쓴다.
    자유도는 Welch-Satterthwaite 근사.
    """
    if min(n0, n1) < 2:
        raise ValueError("그룹마다 2명 이상 있어야 표준편차를 잴 수 있다")
    v0, v1 = sd0 ** 2 / n0, sd1 ** 2 / n1
    se = sqrt(v0 + v1)
    stat = (mean1 - mean0) / se
    df = (v0 + v1) ** 2 / (v0 ** 2 / (n0 - 1) + v1 ** 2 / (n1 - 1))
    p_value = 2 * t.sf(abs(stat), df) if two_sided else t.sf(stat, df)
    return float(stat), float(df), float(p_value)


def student_ttest(mean0, sd0, n0, mean1, sd1, n1, two_sided=True):
    """등분산을 가정하는 Student t 검정. Welch와 비교하려고 둔다. (t, 자유도, p값)"""
    if min(n0, n1) < 2:
        raise ValueError("그룹마다 2명 이상 있어야 표준편차를 잴 수 있다")
    df = n0 + n1 - 2
    sp2 = ((n0 - 1) * sd0 ** 2 + (n1 - 1) * sd1 ** 2) / df
    se = sqrt(sp2 * (1 / n0 + 1 / n1))
    stat = (mean1 - mean0) / se
    p_value = 2 * t.sf(abs(stat), df) if two_sided else t.sf(stat, df)
    return float(stat), float(df), float(p_value)
