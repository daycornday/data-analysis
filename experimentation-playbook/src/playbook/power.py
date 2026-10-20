"""두 비율 비교(A/B 테스트)의 표본 크기, 검정력, MDE 계산.

문서 docs/methods/power-and-sample-size.md 의 식을 그대로 코드로 옮겼다.

    n = (z_alpha + z_beta)^2 * [p0(1-p0) + p1(1-p1)] / (p1 - p0)^2
      = 엄격함^2 * 잡음 / 신호^2
"""
from math import ceil, sqrt

from scipy.stats import norm


def _z_alpha(alpha, two_sided=True):
    return norm.ppf(1 - alpha / 2) if two_sided else norm.ppf(1 - alpha)


def sample_size_per_group(p0, mde, alpha=0.05, power=0.8, two_sided=True):
    """그룹당 필요 표본 수.

    p0  : 대조군 기준 비율 (예 0.10)
    mde : 잡고 싶은 최소 차이, 절대값 %p (예 0.01)
    """
    if not 0 < p0 < 1 or not 0 < p0 + mde < 1:
        raise ValueError("p0와 p0 + mde는 0과 1 사이여야 한다")
    if mde == 0:
        raise ValueError("mde가 0이면 표본 수가 무한대다")
    p1 = p0 + mde
    strictness = _z_alpha(alpha, two_sided) + norm.ppf(power)
    noise = p0 * (1 - p0) + p1 * (1 - p1)
    return ceil(strictness ** 2 * noise / mde ** 2)


def power_given_n(p0, mde, n_per_group, alpha=0.05, two_sided=True):
    """그룹당 n명일 때 검정력. 같은 식을 방향만 바꾼 것.

    SE = sqrt(잡음 / n), 표준화 거리 = |mde| / SE, 검정력 = Phi(표준화 거리 - z_alpha)
    (양측검정의 반대쪽 꼬리는 무시할 만큼 작아서 뺀다)
    """
    p1 = p0 + mde
    se = sqrt((p0 * (1 - p0) + p1 * (1 - p1)) / n_per_group)
    return float(norm.cdf(abs(mde) / se - _z_alpha(alpha, two_sided)))


def mde_given_n(p0, n_per_group, alpha=0.05, power=0.8, two_sided=True):
    """그룹당 n명으로 잡아낼 수 있는 최소 차이(MDE).

    실험이 끝나고 결과가 음성일 때 "이 표본으로는 어느 크기까지 잡을 수 있었나"를
    보고하는 데 쓴다. 관측 효과로 계산하는 사후검정력 대신 이 값을 쓴다.
    잡음이 p1에도 걸려 있어서 이분법으로 푼다.
    """
    lo, hi = 1e-6, 1 - p0 - 1e-6
    for _ in range(100):
        mid = (lo + hi) / 2
        if power_given_n(p0, mid, n_per_group, alpha, two_sided) < power:
            lo = mid
        else:
            hi = mid
    return hi


def days_needed(n_per_group, daily_assigned_total, n_groups=2):
    """하루 배정 인원으로 나눠 필요한 실험 기간(일)을 낸다."""
    return ceil(n_per_group * n_groups / daily_assigned_total)


def bonferroni_alpha(alpha, n_comparisons):
    """비교를 여러 번 할 때 쌍마다 쓸 유의수준."""
    return alpha / n_comparisons


def familywise_error(alpha, n_comparisons):
    """보정 없이 n번 비교할 때 한 번이라도 거짓양성이 나올 확률."""
    return 1 - (1 - alpha) ** n_comparisons
