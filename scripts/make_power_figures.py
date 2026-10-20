"""docs/methods/power-and-sample-size.md 에 들어가는 그림 4장을 만든다.

실행: python scripts/make_power_figures.py  (출력: docs/assets/power/*.png)
모든 값은 가상 시나리오다. 실제 서비스 데이터는 쓰지 않는다.
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import binom, norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from playbook import sample_size_per_group  # noqa: E402

OUT = ROOT / "docs" / "assets" / "power"
OUT.mkdir(parents=True, exist_ok=True)

for font in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
    if any(font == f.name for f in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = font
        break
plt.rcParams["axes.unicode_minus"] = False

RED, TEAL, GRAY, INK = "#d1495b", "#2a9d8f", "#9aa5b1", "#264653"


def coin_flips():
    """경우 A: 동전 10번. 공정(H0, p=0.5)과 조작(H1, p=0.8)을 같은 축에 겹친다."""
    k = np.arange(0, 11)
    h0, h1 = binom.pmf(k, 10, 0.5), binom.pmf(k, 10, 0.8)
    cut = 7
    fig, ax = plt.subplots(figsize=(8, 4))
    w = 0.38
    ax.bar(k - w / 2, h0, w, color=[RED if x >= cut else "#e9c6cb" for x in k], label="H0: 공정한 동전")
    ax.bar(k + w / 2, h1, w, color=[TEAL if x >= cut else GRAY for x in k], label="H1: 앞면 조작")
    ax.axvline(cut - 0.5, color=INK, ls="--")
    alpha, power = h0[k >= cut].sum(), h1[k >= cut].sum()
    ax.set_title(f"판정선 7개 이상: 빨강 α={alpha:.3f}, 청록 검정력={power:.3f}, 회색 β={1 - power:.3f}")
    ax.set_xlabel("앞면 개수 (10번 중)")
    ax.set_ylabel("확률")
    ax.set_xticks(k)
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color="#e9c6cb", label="H0 공정한 동전 (판정선 왼쪽)"),
        Patch(color=RED, label="H0 판정선 오른쪽 = α (거짓 경보)"),
        Patch(color=GRAY, label="H1 판정선 왼쪽 = β (놓침)"),
        Patch(color=TEAL, label="H1 판정선 오른쪽 = 검정력"),
    ], fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "01_coin_two_hills.png", dpi=150)
    plt.close(fig)


def ab_difference():
    """경우 B: A/B 차이축. H0 중심 0, H1 중심 +1%p, 양측 칼금 ±1.96 SE."""
    p0, mde, n = 0.10, 0.01, 14_750
    se = np.sqrt((p0 * (1 - p0) + (p0 + mde) * (1 - p0 - mde)) / n)
    x = np.linspace(-4 * se, mde + 4 * se, 800)
    h0, h1 = norm.pdf(x, 0, se), norm.pdf(x, mde, se)
    cut = 1.96 * se
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x * 100, h0, color=INK, label="H0: 차이 없음 (중심 0)")
    ax.plot(x * 100, h1, color=TEAL, label="H1: +1%p 효과 가정")
    ax.fill_between(x * 100, h1, where=x >= cut, color=TEAL, alpha=0.35, label="검정력 (1-β)")
    ax.fill_between(x * 100, h1, where=x < cut, color=GRAY, alpha=0.45, label="β (놓침)")
    ax.fill_between(x * 100, h0, where=np.abs(x) >= cut, color=RED, alpha=0.6, label="α/2 양쪽 (거짓 경보)")
    for c in (-cut, cut):
        ax.axvline(c * 100, color=INK, ls="--", lw=1)
    ax.set_xlabel("실험군 비율 - 대조군 비율 (%p)")
    ax.set_yticks([])
    ax.set_title("차이의 표본분포: 칼금 ±1.96 SE, 그룹당 14,750명")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "02_ab_difference.png", dpi=150)
    plt.close(fig)


def mde_vs_n():
    """MDE가 줄수록 필요 표본이 제곱으로 늘어난다."""
    mdes = np.linspace(0.003, 0.03, 60)
    ns = [sample_size_per_group(0.10, m) for m in mdes]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(mdes * 100, np.array(ns) / 1000, color=INK)
    for m in (0.005, 0.01, 0.02):
        n = sample_size_per_group(0.10, m)
        ax.scatter([m * 100], [n / 1000], color=RED, zorder=3)
        ax.annotate(f"+{m * 100:.1f}%p → {n:,}명", (m * 100, n / 1000), textcoords="offset points", xytext=(8, 6))
    ax.set_xlabel("MDE (%p, 대조군 10% 기준)")
    ax.set_ylabel("그룹당 필요 표본 (천 명)")
    ax.set_title("잡고 싶은 차이를 절반으로 줄이면 표본은 약 4배")
    fig.tight_layout()
    fig.savefig(OUT / "03_mde_vs_n.png", dpi=150)
    plt.close(fig)


def n_sharpens_hills():
    """같은 효과라도 n을 키우면 두 산이 뾰족해져 겹침이 줄어든다."""
    p0, mde = 0.10, 0.01
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=False)
    for ax, n in zip(axes, (3_000, 15_000)):
        se = np.sqrt((p0 * (1 - p0) + (p0 + mde) * (1 - p0 - mde)) / n)
        x = np.linspace(-0.035, 0.045, 800)
        h0, h1 = norm.pdf(x, 0, se), norm.pdf(x, mde, se)
        cut = 1.96 * se
        ax.plot(x * 100, h0, color=INK)
        ax.plot(x * 100, h1, color=TEAL)
        ax.fill_between(x * 100, np.minimum(h0, h1), color=RED, alpha=0.4)
        ax.axvline(cut * 100, color=INK, ls="--", lw=1)
        power = norm.cdf(mde / se - 1.96)
        ax.set_title(f"그룹당 {n:,}명: 검정력 {power:.0%}")
        ax.set_xlabel("차이 (%p)")
        ax.set_yticks([])
    fig.suptitle("빨강 = 두 산이 겹치는 구간 (오류가 나는 곳)")
    fig.tight_layout()
    fig.savefig(OUT / "04_n_sharpens.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    coin_flips()
    ab_difference()
    mde_vs_n()
    n_sharpens_hills()
    print("saved to", OUT)
