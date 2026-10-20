"""docs/methods/z-vs-t.md 에 들어가는 그림 2장을 만든다.

실행: python scripts/make_z_vs_t_figures.py  (출력: docs/assets/z-vs-t/*.png)
모든 값은 가상 시나리오다. 실제 서비스 데이터는 쓰지 않는다.
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm, t

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from playbook import critical_value  # noqa: E402

OUT = ROOT / "docs" / "assets" / "z-vs-t"
OUT.mkdir(parents=True, exist_ok=True)

for font in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
    if any(font == f.name for f in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = font
        break
plt.rcParams["axes.unicode_minus"] = False

RED, TEAL, GRAY, INK = "#d1495b", "#2a9d8f", "#9aa5b1", "#264653"


def tails():
    """정규분포와 자유도 5인 t분포를 겹친다. t는 꼬리가 두껍다."""
    x = np.linspace(-4.5, 4.5, 600)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x, norm.pdf(x), color=INK, lw=2, label="정규분포 (z)")
    ax.plot(x, t.pdf(x, 5), color=TEAL, lw=2, label="t분포 (자유도 5)")
    z_cut, t_cut = critical_value(), critical_value(df=5)
    ax.axvline(z_cut, color=INK, ls="--")
    ax.axvline(t_cut, color=TEAL, ls="--")
    ax.text(z_cut - 0.08, 0.36, f"z 판정선 {z_cut:.2f}", color=INK, ha="right")
    ax.text(t_cut + 0.08, 0.30, f"t 판정선 {t_cut:.2f}", color=TEAL)
    ax.fill_between(x, t.pdf(x, 5), norm.pdf(x), where=np.abs(x) > 2.2, color=RED, alpha=0.3,
                    label="t가 더 두꺼운 꼬리")
    ax.set_title("표본이 작으면 t는 꼬리가 두꺼워 판정선이 바깥으로 밀린다")
    ax.set_xlabel("표준화한 차이 (차이 ÷ SE)")
    ax.set_ylabel("밀도")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "01_tails.png", dpi=150)
    plt.close(fig)


def critical_by_df():
    """자유도가 커질수록 t 판정선이 1.96으로 붙는다."""
    dfs = np.array([2, 3, 5, 8, 10, 15, 20, 30, 50, 100, 200, 500, 1000])
    crit = [critical_value(df=d) for d in dfs]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dfs, crit, "o-", color=TEAL, label="t 판정선 (양측 5%)")
    ax.axhline(critical_value(), color=RED, ls="--", label="z 판정선 1.96")
    for d in (10, 30, 100):
        c = critical_value(df=d)
        ax.annotate(f"자유도 {d}: {c:.3f}", (d, c), textcoords="offset points", xytext=(8, 10), color=INK)
    ax.set_xscale("log")
    ax.set_ylim(1.8, 4.5)
    ax.set_title("자유도 100이면 차이는 0.02, 온라인 실험 규모에서는 사실상 같다")
    ax.set_xlabel("자유도 (로그 축, 대략 두 그룹 표본 합 - 2)")
    ax.set_ylabel("판정선")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "02_critical_by_df.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    tails()
    critical_by_df()
    print("saved to", OUT)
