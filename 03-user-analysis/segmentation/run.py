"""segmentation의 모든 숫자와 그림을 처음부터 다시 만든다. 실행: python run.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency
from sklearn.metrics import adjusted_rand_score
from statsmodels.stats.proportion import proportion_confint

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "src"))

from segmentation_gmm.synth import FEATURES, SEGMENTS, make_users  # noqa: E402
from segmentation_gmm.compose import shares_from_counts, clr, drop_last  # noqa: E402
from segmentation_gmm.cluster import (  # noqa: E402
    fit_gmm, bic_curve, choose_k, kmeans_labels, segment_profile,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

DATA = HERE / "data"
OUT = HERE / "outputs"
SEED = 7
N_USERS = 6000
K_RANGE = range(1, 9)
N_REPLICATES = 10
LOW_ACTIVITY_EVENTS = [30, 100, 500]


def prepare(df):
    shares = shares_from_counts(df[FEATURES].to_numpy())
    return shares, clr(shares)


def method_labels(shares, z, k, seed):
    """비교할 방법 4가지의 군집 라벨."""
    return {
        "원자료 + k-means": kmeans_labels(shares, k, seed),
        "원자료 + GMM": fit_gmm(drop_last(shares), k, seed).predict(drop_last(shares)),
        "CLR + k-means": kmeans_labels(z, k, seed),
        "CLR + GMM": fit_gmm(drop_last(z), k, seed).predict(drop_last(z)),
    }


def compare_methods(k):
    """데이터를 시드만 바꿔 N_REPLICATES번 새로 만들고 방법별 ARI를 잰다."""
    rows = []
    for r in range(N_REPLICATES):
        df = make_users(N_USERS, seed=SEED + 100 + r)
        shares, z = prepare(df)
        for name, labels in method_labels(shares, z, k, seed=r).items():
            rows.append({"반복": r, "방법": name, "ARI": adjusted_rand_score(df["true_segment"], labels)})
    res = pd.DataFrame(rows)
    summary = res.groupby("방법", sort=False)["ARI"].agg(["mean", "min", "max"]).reset_index()
    summary.columns = ["방법", "ARI 평균", "ARI 최소", "ARI 최대"]
    return summary


def low_activity_check(k):
    """유저당 사용 횟수가 적으면 0회 칸과 pseudocount 때문에 CLR이 흔들린다. 횟수별로 ARI를 다시 잰다."""
    rows = []
    for events in LOW_ACTIVITY_EVENTS:
        df = make_users(N_USERS, mean_events=events, seed=SEED)
        shares, z = prepare(df)
        labels = method_labels(shares, z, k, seed=SEED)
        rows.append({"유저당 평균 사용 횟수": events,
                     "0회 칸 비율": (df[FEATURES] == 0).to_numpy().mean(),
                     "원자료 + k-means": adjusted_rand_score(df["true_segment"], labels["원자료 + k-means"]),
                     "CLR + GMM": adjusted_rand_score(df["true_segment"], labels["CLR + GMM"])})
    return pd.DataFrame(rows)


def plot_raw_vs_clr(df, shares, z):
    names = list(SEGMENTS)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for name in names:
        m = (df["true_segment"] == name).to_numpy()
        axes[0].scatter(shares[m, 0], shares[m, 4], s=4, alpha=0.4, label=name)
        axes[1].scatter(z[m, 0], z[m, 4], s=4, alpha=0.4, label=name)
    axes[0].set_xlabel("편집 비중")
    axes[0].set_ylabel("협업 비중")
    axes[0].set_title("원자료 비중: 협업 차이가 바닥에 눌린다")
    axes[1].set_xlabel("편집 CLR")
    axes[1].set_ylabel("협업 CLR")
    axes[1].set_title("CLR: 작은 비중의 상대 차이가 펴진다")
    axes[1].legend(markerscale=4, loc="lower left")
    fig.suptitle("정답 세그먼트별 편집과 협업 사용 (합성 유저 6,000명)")
    fig.tight_layout()
    fig.savefig(OUT / "raw_vs_clr.png", dpi=120)
    plt.close(fig)


def plot_bic(bics, k_best):
    ks = list(bics)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(ks, [bics[k] for k in ks], marker="o")
    ax.axvline(k_best, color="tab:orange", ls="--", label="최소 BIC: {}개".format(k_best))
    ax.set_xlabel("군집 수")
    ax.set_ylabel("BIC (낮을수록 좋음)")
    ax.set_title("CLR + GMM 군집 수별 BIC")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "bic.png", dpi=120)
    plt.close(fig)


def plot_ari(summary):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    y = np.arange(len(summary))
    err = [summary["ARI 평균"] - summary["ARI 최소"], summary["ARI 최대"] - summary["ARI 평균"]]
    ax.barh(y, summary["ARI 평균"], xerr=err, color="tab:blue", capsize=3)
    for yi, v in zip(y, summary["ARI 평균"]):
        ax.text(v + 0.02, yi, "{:.2f}".format(v), va="center")
    ax.set_yticks(y)
    ax.set_yticklabels(summary["방법"])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.1)
    ax.set_xlabel("ARI (1 = 정답 세그먼트를 그대로 되찾음)")
    ax.set_title("정답을 얼마나 되찾나 (데이터 {}번 새로 생성, 막대 끝 = 최소~최대)".format(N_REPLICATES))
    fig.tight_layout()
    fig.savefig(OUT / "ari_comparison.png", dpi=120)
    plt.close(fig)


def plot_profile(profile):
    shares = profile[FEATURES].to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), gridspec_kw={"width_ratios": [3, 2]})
    axes[0].imshow(shares, cmap="Blues", vmin=0, vmax=0.7, aspect="auto")
    for i in range(shares.shape[0]):
        for j in range(shares.shape[1]):
            axes[0].text(j, i, "{:.0%}".format(shares[i, j]), ha="center", va="center",
                         color="white" if shares[i, j] > 0.4 else "black")
    ylabels = ["{} ({:.0%})".format(n, r) for n, r in zip(profile["이름"], profile["비율"])]
    axes[0].set_xticks(range(len(FEATURES)))
    axes[0].set_xticklabels(FEATURES)
    axes[0].set_yticks(range(len(profile)))
    axes[0].set_yticklabels(ylabels)
    axes[0].set_title("세그먼트별 대표 사용 비중 (괄호 = 유저 비율)")
    y = np.arange(len(profile))
    rate = profile["전환율"].to_numpy()
    err = [rate - profile["하한95"], profile["상한95"] - rate]
    axes[1].barh(y, rate, xerr=err, color="tab:orange", capsize=3)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels(profile["이름"])
    axes[1].invert_yaxis()
    axes[1].set_xlabel("유료 전환율 (95% 구간)")
    axes[1].set_title("세그먼트별 유료 전환율")
    axes[1].xaxis.set_major_locator(plt.MultipleLocator(0.04))
    axes[1].xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: "{:.0%}".format(v)))
    fig.tight_layout()
    fig.savefig(OUT / "segment_profile.png", dpi=120)
    plt.close(fig)


def name_segments(profile, labels, truth):
    """찾은 군집마다 가장 많이 겹치는 정답 세그먼트 이름을 붙인다 (해석용)."""
    names = []
    for g in profile["세그먼트"]:
        names.append(pd.Series(truth[labels == g]).value_counts().index[0])
    return names


def main():
    DATA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    df = make_users(N_USERS, seed=SEED)
    df.to_csv(DATA / "feature_usage.csv", index=False, encoding="utf-8-sig")
    shares, z = prepare(df)
    print("유저 {:,}명, 기능 사용 0회 칸 비율 {:.1%}".format(len(df), (df[FEATURES] == 0).to_numpy().mean()))
    plot_raw_vs_clr(df, shares, z)

    bics = bic_curve(drop_last(z), K_RANGE, seed=SEED)
    k_best = choose_k(bics)
    pd.DataFrame({"군집 수": list(bics), "BIC": list(bics.values())}).round(1).to_csv(
        OUT / "bic.csv", index=False, encoding="utf-8-sig")
    print("BIC 최소 군집 수: {} (정답 {})".format(k_best, len(SEGMENTS)))
    plot_bic(bics, k_best)

    labels_here = method_labels(shares, z, k_best, seed=SEED)
    for name, lab in labels_here.items():
        print("  이 데이터 ARI {}: {:.3f}".format(name, adjusted_rand_score(df["true_segment"], lab)))
    for name in ["원자료 + k-means", "CLR + GMM"]:
        cross = pd.crosstab(df["true_segment"], labels_here[name], rownames=["정답"], colnames=[name])
        cross.to_csv(OUT / "crosstab_{}.csv".format("raw_kmeans" if "k-means" in name else "clr_gmm"),
                     encoding="utf-8-sig")
        print(cross.to_string())
    summary = compare_methods(k_best)
    summary.round(3).to_csv(OUT / "ari_comparison.csv", index=False, encoding="utf-8-sig")
    print(summary.round(3).to_string(index=False))
    plot_ari(summary)
    low = low_activity_check(k_best)
    low.round(3).to_csv(OUT / "low_activity_check.csv", index=False, encoding="utf-8-sig")
    print(low.round(3).to_string(index=False))

    labels = labels_here["CLR + GMM"]
    converted = df["converted"].to_numpy()
    profile = segment_profile(z, labels, converted, FEATURES)
    profile.insert(1, "이름", name_segments(profile, labels, df["true_segment"].to_numpy()))
    lo, hi = proportion_confint(profile["전환 수"], profile["유저 수"], method="wilson")
    profile["하한95"], profile["상한95"] = lo, hi
    profile = profile.sort_values("유저 수", ascending=False).reset_index(drop=True)
    profile.round(3).to_csv(OUT / "segment_profile.csv", index=False, encoding="utf-8-sig")
    print(profile.round(3).to_string(index=False))
    table = np.column_stack([profile["전환 수"], profile["유저 수"] - profile["전환 수"]])
    chi2, p, dof, _ = chi2_contingency(table)
    print("세그먼트 간 전환율 차이 카이제곱 {:.1f}, 자유도 {}, p = {:.2e}".format(chi2, dof, p))
    print("전체 전환율 {:.2%}".format(converted.mean()))
    plot_profile(profile)


if __name__ == "__main__":
    main()
