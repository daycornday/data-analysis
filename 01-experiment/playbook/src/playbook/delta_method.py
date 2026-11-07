"""건수 기준 비율 지표(클릭률, 객단가 등)의 분산을 delta method로 구한다.

문서 docs/methods/delta-method.md 의 식을 그대로 코드로 옮겼다.
배정은 유저 단위인데 지표의 분모가 노출, 주문처럼 유저보다 잘게 쪼개진 단위일 때 쓴다.
입력은 유저마다 한 줄이다. numerator[i]는 i번째 유저의 분자 합(클릭 수),
denominator[i]는 분모 합(노출 수)이다.
"""
from collections import namedtuple

import numpy as np
from scipy.stats import norm

RatioTest = namedtuple("RatioTest", "diff se z p_value ci_low ci_high")
LiftCI = namedtuple("LiftCI", "lift se ci_low ci_high")


def _as_arrays(numerator, denominator):
    x = np.asarray(numerator, dtype=float)
    y = np.asarray(denominator, dtype=float)
    if x.ndim != 1 or x.shape != y.shape:
        raise ValueError("분자와 분모는 유저마다 한 줄씩, 길이가 같아야 한다")
    if len(x) < 2:
        raise ValueError("유저가 두 명 이상 있어야 분산을 잡을 수 있다")
    if y.mean() <= 0:
        raise ValueError("분모 평균이 0보다 커야 한다")
    return x, y


def ratio_delta_var(numerator, denominator):
    """비율 지표 R = sum(x) / sum(y) 와 그 분산(추정량의 분산)을 돌려준다.

    Var(R) ≈ (Var(x) - 2R Cov(x, y) + R² Var(y)) / (n × ȳ²)
    분산과 공분산은 유저 단위로 계산한다(ddof=1).
    """
    x, y = _as_arrays(numerator, denominator)
    n = len(x)
    x_bar, y_bar = x.mean(), y.mean()
    ratio = x_bar / y_bar
    cov = np.cov(x, y, ddof=1)
    var = (cov[0, 0] - 2 * ratio * cov[0, 1] + ratio**2 * cov[1, 1]) / (n * y_bar**2)
    return float(ratio), float(var)


def ratio_ztest(num0, den0, num1, den1, alpha=0.05):
    """두 그룹의 비율 지표 차이(실험군 - 대조군)를 delta method 분산으로 검정한다.

    유저가 수천 명 이상이라 정규 근사로 판정한다. 신뢰구간은 1 - alpha 수준.
    """
    r0, v0 = ratio_delta_var(num0, den0)
    r1, v1 = ratio_delta_var(num1, den1)
    diff = r1 - r0
    se = float(np.sqrt(v0 + v1))
    if se == 0:
        raise ValueError("두 그룹 모두 분산이 0이라 검정할 수 없다")
    z = diff / se
    q = float(norm.ppf(1 - alpha / 2))
    return RatioTest(diff, se, z, float(2 * norm.sf(abs(z))), diff - q * se, diff + q * se)


def relative_lift_ci(mean0, var0, mean1, var1, alpha=0.05):
    """상대 변화율(mean1 / mean0 - 1)의 신뢰구간. 이것도 비율이라 delta method를 쓴다.

    var0, var1 은 각 그룹 추정량의 분산이다(ratio_delta_var의 두 번째 값, 또는 평균의 분산).
    Var(m1 / m0) ≈ var1 / m0² + m1² var0 / m0⁴ (두 그룹은 독립)
    """
    if mean0 <= 0:
        raise ValueError("대조군 값이 0보다 커야 상대 변화율을 정의할 수 있다")
    lift = mean1 / mean0 - 1
    se = float(np.sqrt(var1 / mean0**2 + mean1**2 * var0 / mean0**4))
    q = float(norm.ppf(1 - alpha / 2))
    return LiftCI(lift, se, lift - q * se, lift + q * se)
