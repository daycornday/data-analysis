"""docs/methods/multiple-comparisons.md 에 들어가는 그림 2장을 만든다.

실행: python scripts/make_multiple_comparisons_figures.py  (출력: docs/assets/multiple-comparisons/*.png)
모든 값은 가상 시나리오다. 실제 서비스 데이터는 쓰지 않는다.
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from playbook import familywise_error  # noqa: E402

OUT = ROOT / "docs" / "assets" / "multiple-comparisons"
OUT.mkdir(parents=True, exist_ok=True)

for font in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
    if any(font == f.name for f in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = font
        break
plt.rcParams["axes.unicode_minus"] = False

RED, TEAL, GRAY, INK = "#d1495b", "#2a9d8f", "#9aa5b1", "#264653"
DOC_P = [0.004, 0.011, 0.019, 0.030, 0.041]


def familywise_curve():
    """보정 없이 비교 횟수를 늘리면 한 번이라도 거짓 양성이 나올 확률이 커진다."""
    m = np.arange(1, 31)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(m, [familywise_error(0.05, k) for k in m], "o-", color=RED, ms=4, label="보정 없음")
    ax.plot(m, [familywise_error(0.05 / k, k) for k in m], "o-", color=TEAL, ms=4, label="본페로니 (α ÷ m)")
    for k in (3, 10, 20):
        v = familywise_error(0.05, k)
        ax.annotate(f"{k}번: {v:.0%}", (k, v), textcoords="offset points", xytext=(6, -14), color=INK)
    ax.axhline(0.05, color=GRAY, ls="--")
    ax.set_ylim(0, 0.85)
    ax.set_title("효과가 하나도 없어도 20번 보면 64%는 하나쯤 유의하게 나온다")
    ax.set_xlabel("비교 횟수 m")
    ax.set_ylabel("거짓 양성이 한 번 이상 나올 확률")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.legend(loc="center right")
    fig.tight_layout()
    fig.savefig(OUT / "01_familywise.png", dpi=150)
    plt.close(fig)


def thresholds():
    """같은 p값 다섯 개를 세 방법의 기준선과 겹쳐 본다."""
    m = len(DOC_P)
    k = np.arange(1, m + 1)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(k, [0.05 / m] * m, "s--", color=INK, label="본페로니 기준 α/m")
    ax.plot(k, [0.05 / (m - i + 1) for i in k], "^--", color=GRAY, label="홀름 기준 α/(m-k+1)")
    ax.plot(k, [0.05 * i / m for i in k], "d--", color=TEAL, label="BH 기준 (k/m)α")
    ax.plot(k, DOC_P, "o", color=RED, ms=9, label="관측 p값 (작은 순)")
    for i, p in zip(k, DOC_P):
        ax.annotate(f"{p:.3f}", (i, p), textcoords="offset points", xytext=(8, -4), color=RED)
    ax.set_xticks(k)
    ax.set_ylim(0, 0.056)
    ax.set_title("빨간 점이 선 아래면 통과. 본페로니 1개, 홀름 2개, BH 5개")
    ax.set_xlabel("p값 순서 k")
    ax.set_ylabel("p값과 기준")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "02_thresholds.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    familywise_curve()
    thresholds()
    print("saved to", OUT)
