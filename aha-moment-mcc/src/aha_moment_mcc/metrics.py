"""혼동행렬, aha-ratio(자카드 지수), MCC, 문턱 훑기."""
import numpy as np
import pandas as pd


def confusion(pred, actual):
    """0/1 예측과 0/1 실제로 TP, FP, FN, TN을 센다."""
    pred = np.asarray(pred).astype(bool)
    actual = np.asarray(actual).astype(bool)
    tp = int(np.sum(pred & actual))
    fp = int(np.sum(pred & ~actual))
    fn = int(np.sum(~pred & actual))
    tn = int(np.sum(~pred & ~actual))
    return tp, fp, fn, tn


def aha_ratio(tp, fp, fn, tn=None):
    """TP / (TP + FP + FN). 행동자 집합과 잔존자 집합의 자카드 지수. TN은 쓰지 않는다."""
    union = tp + fp + fn
    return tp / union if union else 0.0


def mcc(tp, fp, fn, tn):
    """매튜스 상관계수. 한쪽 합이 0이면 정의상 0으로 둔다."""
    denom = float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    if denom == 0:
        return 0.0
    return (float(tp) * tn - float(fp) * fn) / np.sqrt(denom)


def scores(tp, fp, fn, tn):
    """한 혼동행렬의 지표 묶음. 정밀도는 예측 양성이 0이면 NaN."""
    n = tp + fp + fn + tn
    base = (tp + fn) / n
    precision = tp / (tp + fp) if (tp + fp) else np.nan
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "pred_pos_rate": (tp + fp) / n,
        "accuracy": (tp + tn) / n,
        "precision": precision,
        "recall": tp / (tp + fn) if (tp + fn) else np.nan,
        "lift": precision / base if base else np.nan,
        "mcc": mcc(tp, fp, fn, tn),
        "aha_ratio": aha_ratio(tp, fp, fn),
    }


def sweep_thresholds(count, retained, thresholds):
    """문턱 N마다 'count >= N이면 남을 것'으로 예측하고 지표를 계산한다."""
    rows = []
    for n_cut in thresholds:
        row = scores(*confusion(np.asarray(count) >= n_cut, retained))
        row["N"] = n_cut
        rows.append(row)
    cols = ["N"] + [c for c in rows[0] if c != "N"]
    return pd.DataFrame(rows)[cols]


def plateau(table, col="mcc", share=0.95):
    """col 값이 최댓값의 share 이상인 N 목록."""
    best = table[col].max()
    return table.loc[table[col] >= share * best, "N"].tolist()
