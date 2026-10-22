"""BIC로 군집 수를 고르는 GMM, 비교용 k-means, 세그먼트 프로파일."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture

from .compose import clr_inverse


def fit_gmm(z, k, seed=0):
    return GaussianMixture(n_components=k, covariance_type="full", n_init=5, random_state=seed).fit(z)


def bic_curve(z, k_range, seed=0):
    """군집 수별 BIC. 낮을수록 좋다."""
    return {k: fit_gmm(z, k, seed).bic(z) for k in k_range}


def choose_k(bics):
    return min(bics, key=bics.get)


def kmeans_labels(x, k, seed=0):
    return KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(x)


def segment_profile(z, labels, converted, features):
    """세그먼트별 크기, 대표 비중(CLR 평균을 되돌린 값), 유료 전환율."""
    rows = []
    for g in np.unique(labels):
        m = labels == g
        center = clr_inverse(z[m].mean(axis=0, keepdims=True))[0]
        row = {"세그먼트": int(g), "유저 수": int(m.sum()), "비율": m.mean()}
        row.update({f: c for f, c in zip(features, center)})
        row["전환 수"] = int(converted[m].sum())
        row["전환율"] = converted[m].mean()
        rows.append(row)
    return pd.DataFrame(rows)
