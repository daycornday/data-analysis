"""docs/methods/delta-method.md 에 들어가는 그림 2장을 만든다.

실행: python scripts/make_delta_method_figures.py  (출력: docs/assets/delta-method/*.png)
모든 값은 가상 시나리오다. 실제 서비스 데이터는 쓰지 않는다.
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from playbook import ratio_delta_var, ratio_ztest, two_proportion_ztest  # noqa: E402

OUT = ROOT / "docs" / "assets" / "delta-method"
OUT.mkdir(parents=True, exist_ok=True)

for font in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
    if any(font == f.name for f in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = font
        break
plt.rcParams["axes.unicode_minus"] = False

RED, TEAL, GRAY, INK = "#d1495b", "#2a9d8f", "#9aa5b1", "#264653"


def simulate_users(rng, n, mean_impressions=10, ctr_a=2.0):
    """유저마다 노출 수와 평소 클릭 성향이 다른 가상 데이터. 클릭률 평균은 약 10%."""
    if mean_impressions > 1:
        imp = rng.negative_binomial(2, 2 / (2 + mean_impressions - 1), size=n) + 1
    else:
        imp = np.ones(n, dtype=int)
    ctr = rng.beta(ctr_a, 18, size=n)
    return rng.binomial(imp, ctr), imp


def aa_pvalues(sims=2_000, n=5_000, seed=42):
    """차이가 전혀 없는 두 그룹(A/A)을 반복해서 두 방법의 p값을 모은다."""
    rng = np.random.default_rng(seed)
    naive, delta = [], []
    for _ in range(sims):
        c0, i0 = simulate_users(rng, n)
        c1, i1 = simulate_users(rng, n)
        naive.append(two_proportion_ztest(c0.sum(), i0.sum(), c1.sum(), i1.sum(), pooled=False)[1])
        delta.append(ratio_ztest(c0, i0, c1, i1).p_value)
    return np.array(naive), np.array(delta)


def aa_histograms():
    naive, delta = aa_pvalues()
    rates = {"naive": (naive < 0.05).mean(), "delta": (delta < 0.05).mean()}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    bins = np.linspace(0, 1, 21)
    for ax, p, color, name in (
        (axes[0], naive, RED, "노출 단위로 계산"),
        (axes[1], delta, TEAL, "delta method"),
    ):
        ax.hist(p, bins=bins, color=color, edgecolor="white")
        ax.axhline(len(p) / 20, color=GRAY, ls="--")
        ax.set_title(f"{name}: p < 0.05가 {(p < 0.05).mean():.1%}")
        ax.set_xlabel("A/A 실험의 p값")
    axes[0].set_ylabel("횟수 (2,000번 중)")
    fig.suptitle("차이가 없는 실험인데 왼쪽은 0 근처 p값이 너무 많다", color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "01_aa_pvalues.png", dpi=150)
    plt.close(fig)
    return rates


def se_inflation():
    """유저당 노출이 많을수록 노출 단위 SE가 실제보다 더 작게 나온다."""
    means = [1, 2, 5, 10, 20, 50]
    ratios = []
    for m in means:
        clk, imp = simulate_users(np.random.default_rng(1), 40_000, mean_impressions=m)
        r, v = ratio_delta_var(clk, imp)
        ratios.append(np.sqrt(v / (r * (1 - r) / imp.sum())))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(means, ratios, "o-", color=INK)
    for m, s in zip(means, ratios):
        ax.annotate(f"{s:.2f}배", (m, s), textcoords="offset points", xytext=(-4, 9), ha="right", color=INK)
    ax.axhline(1, color=GRAY, ls="--")
    ax.set_xscale("log")
    ax.set_xlim(0.6, 70)
    ax.set_ylim(0.9, 2.3)
    ax.set_xticks(means)
    ax.set_xticklabels([str(m) for m in means])
    ax.set_title("유저당 노출이 많을수록 노출 단위 계산이 SE를 더 작게 잡는다")
    ax.set_xlabel("유저당 평균 노출 수 (로그 축)")
    ax.set_ylabel("delta SE ÷ 노출 단위 SE")
    fig.tight_layout()
    fig.savefig(OUT / "02_se_inflation.png", dpi=150)
    plt.close(fig)
    return dict(zip(means, ratios))


if __name__ == "__main__":
    print("A/A false positive rate", aa_histograms())
    print("SE ratio by impressions", se_inflation())
    print("saved to", OUT)
