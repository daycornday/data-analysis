"""markov-growth의 모든 숫자와 그림을 처음부터 다시 만든다. 실행: python run.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "src"))

from growth_markov.chain import STATES, LABELS, true_transition_matrix, simulate_logs  # noqa: E402
from growth_markov.estimate import estimate_matrix, bootstrap_matrices  # noqa: E402
from growth_markov.project import (  # noqa: E402
    LEVERS, steady_state, project, active_users, improve, sensitivity,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

DATA = HERE / "data"
OUT = HERE / "outputs"
NEW_PER_MONTH = 2000
MONTHS_OBSERVED = 24
HORIZON = 12
N_BOOT = 200
SEED = 42
LABEL = dict(zip(STATES, LABELS))


def lever_name(lever):
    return "{} → {}".format(LABEL[lever[0]], LABEL[lever[1]])


def current_stock(logs):
    """관측 마지막 달의 상태별 인원 (이탈 제외). 투영의 출발점."""
    last = logs[logs["month"] == logs["month"].max()]
    counts = last["state"].value_counts()
    x0 = np.array([counts.get(s, 0) for s in STATES], dtype=float)
    x0[STATES.index("churned")] = 0.0
    return x0


def save_matrix_table(P_hat, boots, P_true):
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    rows = []
    for i, s in enumerate(STATES[:-1]):
        for j, d in enumerate(STATES):
            if P_true[i, j] > 0 or P_hat[i, j] > 0:
                rows.append({"출발": LABEL[s], "도착": LABEL[d], "추정": P_hat[i, j],
                             "하한95": lo[i, j], "상한95": hi[i, j], "정답": P_true[i, j]})
    table = pd.DataFrame(rows).round(4)
    table.to_csv(OUT / "transition_matrix.csv", index=False, encoding="utf-8-sig")
    covered = ((table["하한95"] <= table["정답"]) & (table["정답"] <= table["상한95"])).mean()
    return table, covered


def plot_heatmap(P_hat):
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(P_hat[:-1], cmap="Blues", vmin=0, vmax=1)
    for i in range(len(STATES) - 1):
        for j in range(len(STATES)):
            v = P_hat[i, j]
            if v > 0:
                ax.text(j, i, "{:.2f}".format(v), ha="center", va="center",
                        color="white" if v > 0.5 else "black", fontsize=9)
    ax.set_xticks(range(len(STATES)))
    ax.set_xticklabels(LABELS, rotation=30)
    ax.set_yticks(range(len(STATES) - 1))
    ax.set_yticklabels(LABELS[:-1])
    ax.set_xlabel("다음 달 상태")
    ax.set_ylabel("이번 달 상태")
    ax.set_title("추정 월간 전이행렬 (합성 로그)")
    fig.tight_layout()
    fig.savefig(OUT / "transition_heatmap.png", dpi=120)
    plt.close(fig)


def plot_projection(P_hat, boots, x0, best):
    months = np.arange(HORIZON + 1)
    base = active_users(project(P_hat, x0, NEW_PER_MONTH, HORIZON))
    better = active_users(project(improve(P_hat, *best), x0, NEW_PER_MONTH, HORIZON))
    band = np.array([active_users(project(B, x0, NEW_PER_MONTH, HORIZON)) for B in boots])
    lo, hi = np.percentile(band, [2.5, 97.5], axis=0)
    steady = active_users(steady_state(P_hat, NEW_PER_MONTH))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.fill_between(months, lo, hi, color="tab:blue", alpha=0.2, label="현재 그대로 95% 구간")
    ax.plot(months, base, color="tab:blue", label="현재 그대로")
    ax.plot(months, better, color="tab:orange", label="{} +1%p".format(lever_name(best)))
    ax.axhline(steady, color="gray", ls="--", label="정상상태 ({:,.0f}명)".format(steady))
    ax.set_xlabel("개월 후")
    ax.set_ylabel("활성 유저 수 (첫 달 활성 + 활성 + 복귀)")
    ax.set_title("12개월 활성 유저 투영 (매달 신규 {:,}명)".format(NEW_PER_MONTH))
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "projection.png", dpi=120)
    plt.close(fig)
    return base, better


def sensitivity_table(P_hat, boots, x0):
    up = sensitivity(P_hat, x0, NEW_PER_MONTH, HORIZON, 0.01)
    down = sensitivity(P_hat, x0, NEW_PER_MONTH, HORIZON, -0.01)
    boot_up = np.array([[sensitivity(B, x0, NEW_PER_MONTH, HORIZON, 0.01)[lv] for lv in LEVERS] for B in boots])
    base_ss = active_users(steady_state(P_hat, NEW_PER_MONTH))
    rows = []
    for k, lv in enumerate(LEVERS):
        long_run = active_users(steady_state(improve(P_hat, *lv), NEW_PER_MONTH)) - base_ss
        rows.append({"레버": lever_name(lv), "현재 확률": P_hat[STATES.index(lv[0]), STATES.index(lv[1])],
                     "+1%p 12개월 증가": up[lv], "하한95": np.percentile(boot_up[:, k], 2.5),
                     "상한95": np.percentile(boot_up[:, k], 97.5), "-1%p 12개월 변화": down[lv],
                     "+1%p 정상상태 증가": long_run})
    table = pd.DataFrame(rows).sort_values("+1%p 12개월 증가", ascending=False).reset_index(drop=True)
    first = np.argmax(boot_up, axis=1)
    top_share = (first == LEVERS.index(_lever_by_name(table.loc[0, "레버"]))).mean()
    table.round(3).to_csv(OUT / "sensitivity.csv", index=False, encoding="utf-8-sig")
    return table, top_share


def _lever_by_name(name):
    return [lv for lv in LEVERS if lever_name(lv) == name][0]


def plot_tornado(table):
    t = table.iloc[::-1]
    y = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(y, t["+1%p 12개월 증가"], color="tab:orange", label="+1%p 개선")
    ax.barh(y, t["-1%p 12개월 변화"], color="tab:blue", label="-1%p 악화")
    err = [t["+1%p 12개월 증가"] - t["하한95"], t["상한95"] - t["+1%p 12개월 증가"]]
    ax.errorbar(t["+1%p 12개월 증가"], y, xerr=err, fmt="none", ecolor="black", capsize=3)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(t["레버"])
    ax.set_xlabel("12개월 뒤 활성 유저 변화 (명)")
    ax.set_title("전이확률 하나를 1%p 바꿨을 때 12개월 뒤 활성 유저")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "tornado.png", dpi=120)
    plt.close(fig)


def main():
    DATA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    P_true = true_transition_matrix()
    logs = simulate_logs(P_true, MONTHS_OBSERVED, NEW_PER_MONTH, seed=SEED)
    logs.to_csv(DATA / "state_logs.csv.gz", index=False, compression="gzip")
    print("로그: 유저 {:,}명, 유저-월 {:,}행".format(logs["user_id"].nunique(), len(logs)))

    P_hat = estimate_matrix(logs)
    boots = bootstrap_matrices(logs, N_BOOT, seed=SEED)
    matrix_table, covered = save_matrix_table(P_hat, boots, P_true)
    print("전이 추정 최대 오차 {:.4f}, 95% 구간이 정답을 덮은 칸 비율 {:.0%}".format(
        np.abs(P_hat - P_true).max(), covered))
    plot_heatmap(P_hat)

    x0 = current_stock(logs)
    ss = steady_state(P_hat, NEW_PER_MONTH)
    print("현재 활성 유저 {:,.0f}명, 정상상태 활성 유저 {:,.0f}명".format(active_users(x0), active_users(ss)))
    pd.DataFrame({"상태": LABELS[:-1], "현재": x0[:-1], "정상상태": ss[:-1]}).round(0).to_csv(
        OUT / "steady_state.csv", index=False, encoding="utf-8-sig")

    table, top_share = sensitivity_table(P_hat, boots, x0)
    print(table.round(1).to_string())
    print("부트스트랩에서 1위 레버가 1위로 나온 비율 {:.0%}".format(top_share))
    plot_tornado(table)
    best = _lever_by_name(table.loc[0, "레버"])
    base, better = plot_projection(P_hat, boots, x0, best)
    print("12개월 뒤 활성 유저: 현재 그대로 {:,.0f}명, {} +1%p {:,.0f}명".format(
        base[-1], lever_name(best), better[-1]))


if __name__ == "__main__":
    main()
