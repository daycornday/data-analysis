"""조성 데이터 변환: 닫기(합 1), 0 처리, CLR."""
import numpy as np


def closure(x):
    x = np.asarray(x, dtype=float)
    return x / x.sum(axis=1, keepdims=True)


def shares_from_counts(counts, pseudocount=0.5):
    """사용 횟수를 비중으로. 0회 기능은 log를 쓸 수 없어서 횟수에 pseudocount를 더한 뒤 닫는다."""
    return closure(np.asarray(counts, dtype=float) + pseudocount)


def clr(shares):
    """중심 로그비 변환: log(x_j / 기하평균(x)). 행 합이 0이 되고 비율만 남는다."""
    logx = np.log(shares)
    return logx - logx.mean(axis=1, keepdims=True)


def clr_inverse(z):
    return closure(np.exp(z))


def drop_last(z):
    """CLR 좌표는 합이 0이라 마지막 열이 나머지로 정해진다. GMM에는 마지막 열을 뺀 D-1개만 넣는다.

    공분산이 특이행렬이 되는 것을 막는다. GMM은 선형 변환에 대해 같은 군집을 내므로 어느 열을 빼도 결과는 같다.
    """
    return np.asarray(z)[:, :-1]
