"""여러 번 검정할 때 쓰는 보정 세 가지 (본페로니, 홀름, BH).

문서 docs/methods/multiple-comparisons.md 의 절차를 그대로 코드로 옮겼다.
세 함수 모두 (기각 여부 목록, 보정한 p값 목록)을 입력 순서대로 돌려준다.
보정한 p값은 원래 alpha와 바로 비교하면 되는 값이다.
"""


def _check(p_values):
    p = [float(x) for x in p_values]
    if not p:
        raise ValueError("p값이 하나도 없다")
    if any(not 0 <= x <= 1 for x in p):
        raise ValueError("p값은 0과 1 사이여야 한다")
    return p


def bonferroni(p_values, alpha=0.05):
    """모든 p값에 비교 횟수 m을 곱한다. alpha / m 과 비교하는 것과 같다."""
    p = _check(p_values)
    m = len(p)
    adjusted = [min(1.0, x * m) for x in p]
    return [a <= alpha for a in adjusted], adjusted


def holm(p_values, alpha=0.05):
    """작은 p값부터 alpha/m, alpha/(m-1), ... 과 비교하다가 처음 실패하면 멈춘다.

    보정한 p값은 k번째로 작은 p값에 (m - k + 1)을 곱하고,
    앞 순서보다 작아지지 않게 누적 최댓값을 잡은 것이다.
    """
    p = _check(p_values)
    m = len(p)
    order = sorted(range(m), key=lambda i: p[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, p[i] * (m - rank)))
        adjusted[i] = running
    return [a <= alpha for a in adjusted], adjusted


def benjamini_hochberg(p_values, alpha=0.05):
    """k번째로 작은 p값을 (k / m) * alpha 와 비교해서, 만족하는 가장 큰 k까지 모두 기각한다.

    FWER이 아니라 FDR(기각한 것 중 거짓의 비율 기댓값)을 alpha 이하로 묶는다.
    보정한 p값은 p * m / k 를 큰 쪽부터 누적 최솟값으로 잡은 것이다.
    """
    p = _check(p_values)
    m = len(p)
    order = sorted(range(m), key=lambda i: p[i], reverse=True)
    adjusted = [0.0] * m
    running = 1.0
    for back, i in enumerate(order):
        k = m - back
        running = min(running, p[i] * m / k)
        adjusted[i] = running
    return [a <= alpha for a in adjusted], adjusted
