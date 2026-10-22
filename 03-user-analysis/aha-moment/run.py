"""아하모먼트 문턱 고르기: aha-ratio와 MCC 비교. 이 폴더의 모든 숫자와 그림을 재현한다."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "src"))
from aha_moment_mcc import make_users, confusion, scores, sweep_thresholds, plateau  # noqa: E402

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

SEED = 20261020
THRESHOLDS = list(range(1, 31))


def describe_data(df):
    y, cnt = df["retained"], df["count"]
    print("유저 수: {:,}".format(len(df)))
    print("잔존 유저: {:,}명, 기저율 {:.2%}".format(y.sum(), y.mean()))
    print("행동 0회 비율 {:.2%}, 중앙값 {:.0f}회, 평균 {:.2f}회, 90분위 {:.0f}회".format(
        (cnt == 0).mean(), cnt.median(), cnt.mean(), cnt.quantile(0.9)))


def baseline_table(df):
    """정보를 쓰지 않는 예측기 세 개의 지표."""
    y = df["retained"].values
    coin = np.random.default_rng(SEED + 1).random(len(y)) < 0.5
    preds = {
        "전원 안 남음": np.zeros(len(y), dtype=bool),
        "전원 남음": np.ones(len(y), dtype=bool),
        "동전 던지기 50%": coin,
    }
    rows = []
    for name, pred in preds.items():
        s = scores(*confusion(pred, y))
        s["예측기"] = name
        rows.append(s)
    return pd.DataFrame(rows)[["예측기", "accuracy", "aha_ratio", "mcc", "precision", "recall"]]


def check_phi(df, n_cut):
    """MCC 공식과 np.corrcoef(0/1 피어슨 상관)이 같은지."""
    pred = (df["count"] >= n_cut).astype(int).values
    y = df["retained"].values
    m = scores(*confusion(pred, y))["mcc"]
    r = np.corrcoef(pred, y)[0, 1]
    slope_fit = np.polyfit(pred, y, 1)[0]
    slope_r = r * y.std() / pred.std()
    print("N={}: MCC {:.6f}, corrcoef {:.6f}, 차이 {:.2e}, R^2 {:.4f}".format(n_cut, m, r, abs(m - r), r ** 2))
    print("회귀 기울기: polyfit {:.4f}, r x (sy/sx) {:.4f}".format(slope_fit, slope_r))
    return m, r


def mcc_split(tp, fp, fn, tn):
    """MCC = 잘 맞힌 정도(TP x TN) - 헛짚은 정도(FP x FN), 같은 분모."""
    denom = np.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    good, bad = float(tp) * tn / denom, float(fp) * fn / denom
    print("분모 {:,.0f}, 잘 맞힌 정도 {:.4f}, 헛짚은 정도 {:.4f}, MCC {:.4f}".format(denom, good, bad, good - bad))


def plot_curves(table, base, aha_pick, mcc_pick, mcc_plateau, path):
    fig, axes = plt.subplots(2, 1, figsize=(8, 7), sharex=True)

    ax = axes[0]
    ax.plot(table["N"], table["aha_ratio"] * 100, marker="o", color="#d1603d")
    ax.axhline(base * 100, color="gray", linestyle="--", linewidth=1)
    ax.text(30, base * 100 + 0.15, "무정보 기준선 = 기저율 {:.2f}%".format(base * 100),
            ha="right", color="gray", fontsize=9)
    ax.axvline(aha_pick, color="#d1603d", linestyle=":", linewidth=1)
    ax.set_ylabel("aha-ratio (%)")
    ax.set_title("aha-ratio: 기저율 근처에 눌려 작은 N(N={})을 고른다".format(aha_pick))

    ax = axes[1]
    ax.axvspan(min(mcc_plateau) - 0.5, max(mcc_plateau) + 0.5, color="#2a6f97", alpha=0.08)
    ax.plot(table["N"], table["mcc"], marker="o", color="#2a6f97")
    ax.axhline(0, color="gray", linestyle="--", linewidth=1)
    ax.text(30, 0.004, "무정보 기준선 = 0", ha="right", color="gray", fontsize=9)
    ax.axvline(mcc_pick, color="#2a6f97", linestyle=":", linewidth=1)
    ax.set_ylabel("MCC")
    ax.set_xlabel("문턱 N (가입 후 7일 안 핵심 행동 횟수 N회 이상)")
    ax.set_title("MCC: 최고점 N={}, 음영은 고원 N={}~{} (최댓값의 95% 안팎)".format(
        mcc_pick, min(mcc_plateau), max(mcc_plateau)))
    ax.set_ylim(-0.005, table["mcc"].max() * 1.2)

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    out = HERE / "outputs"
    data_dir = HERE / "data"
    out.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    df = make_users(SEED)
    df.to_csv(data_dir / "synthetic_users.csv", index=False)
    describe_data(df)
    base = df["retained"].mean()

    print("\n[무정보 예측기]")
    baselines = baseline_table(df)
    print(baselines.round(4).to_string(index=False))
    baselines.to_csv(out / "baselines.csv", index=False)

    table = sweep_thresholds(df["count"], df["retained"], THRESHOLDS)
    table.to_csv(out / "threshold_sweep.csv", index=False)

    aha_pick = int(table.loc[table["aha_ratio"].idxmax(), "N"])
    mcc_pick = int(table.loc[table["mcc"].idxmax(), "N"])
    mcc_plateau = plateau(table, "mcc", 0.95)

    print("\n[N = {} 혼동행렬]".format(mcc_pick))
    row = table.set_index("N").loc[mcc_pick]
    print("TP {:,} FP {:,} FN {:,} TN {:,} (TN 비중 {:.1%})".format(
        int(row.tp), int(row.fp), int(row.fn), int(row.tn), row.tn / len(df)))
    print("정확도 {:.2%}, aha-ratio(자카드) {:.2%}".format(row.accuracy, row.aha_ratio))
    mcc_split(int(row.tp), int(row.fp), int(row.fn), int(row.tn))
    check_phi(df, mcc_pick)

    print("\n[문턱 훑기 N=1~30]")
    show = table[["N", "pred_pos_rate", "precision", "recall", "lift", "mcc", "aha_ratio"]]
    print(show.round(4).to_string(index=False))

    a = table.set_index("N")
    print("\naha-ratio 최고 N = {} ({:.2%}), 기준선보다 {:.2f}%p 높음".format(
        aha_pick, a.loc[aha_pick, "aha_ratio"], (a.loc[aha_pick, "aha_ratio"] - base) * 100))
    print("MCC 최고 N = {} ({:.4f})".format(mcc_pick, a.loc[mcc_pick, "mcc"]))
    print("MCC 최댓값의 95% 이상 N: {}".format(mcc_plateau))

    picks = [("aha-ratio 최고", aha_pick), ("MCC 최고", mcc_pick),
             ("고원 왼쪽 끝", min(mcc_plateau)), ("고원 오른쪽 끝", max(mcc_plateau))]
    comp = pd.DataFrame([dict(기준=name, N=n_cut, **a.loc[n_cut].to_dict()) for name, n_cut in picks])
    comp = comp[["기준", "N", "pred_pos_rate", "precision", "recall", "lift", "mcc", "aha_ratio"]]
    comp.to_csv(out / "picked_thresholds.csv", index=False)
    print("\n[고른 문턱 비교]")
    print(comp.round(4).to_string(index=False))

    plot_curves(table, base, aha_pick, mcc_pick, mcc_plateau, out / "aha_vs_mcc.png")
    print("\n그림 저장: outputs/aha_vs_mcc.png")


if __name__ == "__main__":
    main()
