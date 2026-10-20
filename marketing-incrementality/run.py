"""이 폴더의 모든 숫자와 그림을 처음부터 다시 만든다.

python run.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "src"))
from marketing_incrementality import geo, lift, mmm  # noqa: E402

DATA = HERE / "data"
OUT = HERE / "outputs"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.edgecolor"] = "#52514e"
plt.rcParams["axes.labelcolor"] = "#0b0b0b"
plt.rcParams["xtick.color"] = "#52514e"
plt.rcParams["ytick.color"] = "#52514e"
plt.rcParams["grid.color"] = "#e4e3df"

BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#9a9890"
INK, INK2 = "#0b0b0b", "#52514e"
LABEL = {"tv": "TV", "search": "검색", "social": "소셜"}
COLOR = {"tv": BLUE, "search": ORANGE, "social": AQUA}

# 한 세계의 정답: 채널별 진짜 평균 ROI (증분 매출 / 광고비)
TRUE_ROI = {"tv": 1.8, "search": 1.2, "social": 2.5}
# MMM 정답 변환 모수: (adstock 이월률, hill 반포화점 = adstock 평균의 몇 배, hill 모양)
TRUE_PARAMS = {"tv": (0.65, 1.2, 2.0), "search": (0.1, 0.5, 1.0), "social": (0.3, 1.6, 2.0)}


def won(x):
    return "{:,.0f}".format(x)


def save_table(df, name):
    df.to_csv(OUT / (name + ".csv"), index=False, encoding="utf-8-sig")
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.values]
    (OUT / (name + ".md")).write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 1. 홀드아웃
def run_lift():
    aov, uplift = 30000, 0.008
    cost_per_user = uplift * aov / TRUE_ROI["social"]  # 설계상 iROAS = 2.5
    users = lift.simulate_users(true_uplift=uplift, mean_order_value=aov,
                                cost_per_user=cost_per_user)
    users.to_csv(DATA / "lift_users.csv.gz", index=False, compression="gzip")
    res = lift.estimate_lift(users)
    table = lift.attribution_vs_increment(users, res)
    true_iroas = users["true_incremental_revenue"].sum() / res["cost"]

    print("[1] 홀드아웃 리프트 (소셜 리타겟팅)")
    print("  노출 {:,}명, 홀드아웃 {:,}명".format(res["n_treated"], res["n_holdout"]))
    print("  구매율 {:.2%} vs {:.2%}, 증분 {:.2f}%p (95% CI {:.2f}~{:.2f})".format(
        res["rate_treated"], res["rate_holdout"], res["uplift"] * 100,
        res["uplift_ci"][0] * 100, res["uplift_ci"][1] * 100))
    print("  증분 구매 {:,.0f}건 (정답 {:,}건)".format(
        res["incremental_conversions"], users["true_incremental"].sum()))
    print("  iROAS {:.2f} (95% CI {:.2f}~{:.2f}), 정답 {:.2f}".format(
        res["iroas"], res["iroas_ci"][0], res["iroas_ci"][1], true_iroas))

    show = table.copy()
    show["매출(원)"] = show.pop("매출").map(won)
    show["ROAS"] = show["ROAS"].map("{:.2f}".format)
    show["정답 대비"] = (table["매출"] / table["매출"].iloc[3]).map("{:.1f}배".format)
    save_table(show, "lift_attribution_vs_increment")
    print(show.to_string(index=False))

    fig, ax = plt.subplots(figsize=(8, 3.6))
    labels = ["노출 그룹 전체 매출", "마지막 클릭 기여", "증분 추정 (홀드아웃)", "증분 정답"]
    colors = [GRAY, GRAY, BLUE, INK2]
    y = np.arange(len(labels))[::-1]
    ax.barh(y, table["ROAS"], color=colors, height=0.6)
    lo, hi = res["iroas_ci"]
    ax.errorbar(res["iroas"], y[2], xerr=[[res["iroas"] - lo], [hi - res["iroas"]]],
                fmt="none", ecolor=INK, capsize=4, lw=1.5)
    for i, (yi, v) in enumerate(zip(y, table["ROAS"])):
        right = hi if i == 2 else v
        text = "{:.2f} (95% CI {:.2f}~{:.2f})".format(v, lo, hi) if i == 2 else "{:.2f}".format(v)
        ax.text(right + 0.2, yi, text, va="center", color=INK, fontsize=10)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("ROAS (매출 / 광고비)")
    ax.set_title("같은 캠페인, 기준에 따라 ROAS가 4배 가까이 다르다", loc="left", color=INK)
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "lift_attribution_vs_increment.png", dpi=150)
    plt.close(fig)

    holdout_cost = res["n_holdout"] * uplift * aov
    return res, true_iroas, table, holdout_cost


# ---------------------------------------------------------------- 2. 지역 실험
def run_geo():
    panel = geo.simulate_geo(true_iroas=TRUE_ROI["tv"])
    panel.to_csv(DATA / "geo_panel.csv", index=False)
    res = geo.did_estimate(panel)
    pre = geo.pretrend_test(panel)
    true_inc = panel["true_lift"].sum()
    n_pre = int(panel.loc[panel["post"] == 0, "week"].max()) + 1

    print("\n[2] 지역 실험 (TV), 지역 {}곳, 사전 {}주, 사후 {}주".format(
        panel["region"].nunique(), n_pre, panel["week"].nunique() - n_pre))
    print("  사전 추세 차이 기울기 {:.3f}/주 (p={:.2f})".format(pre["slope"], pre["p_value"]))
    print("  지역-주당 증분 {:.2f} (95% CI {:.2f}~{:.2f}), 정답 평균 {:.2f}".format(
        res["att"], res["att_ci"][0], res["att_ci"][1],
        panel.loc[panel["spend"] > 0, "true_lift"].mean()))
    print("  증분 매출 {:,.0f} (정답 {:,.0f}) 백만 원, 광고비 {:,.0f}".format(
        res["incremental_sales"], true_inc, res["spend"]))
    print("  iROAS {:.2f} (95% CI {:.2f}~{:.2f}), 정답 {:.2f}".format(
        res["iroas"], res["iroas_ci"][0], res["iroas_ci"][1], TRUE_ROI["tv"]))

    m = geo.weekly_means(panel)
    pre_gap = m.loc[m.index < n_pre, "gap"].mean()
    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True,
                             gridspec_kw={"height_ratios": [3, 2]})
    ax = axes[0]
    ax.plot(m.index, m["treated"], color=BLUE, lw=2, label="처치 지역 (TV 켬)")
    ax.plot(m.index, m["control"], color=ORANGE, lw=2, label="통제 지역")
    ax.set_ylabel("지역 평균 주간 매출 (백만 원)")
    ax.set_title("사전 기간에는 나란히, 광고를 켠 뒤 처치 지역만 올라간다", loc="left", color=INK)
    ax.legend(frameon=False, loc="upper left")
    ax = axes[1]
    ax.plot(m.index, m["gap"], color=INK2, lw=2, marker="o", ms=4)
    ax.axhline(pre_gap, color=GRAY, lw=1, ls="--")
    ax.text(n_pre + 0.5, pre_gap - 0.4, "사전 평균 차이 {:.1f}".format(pre_gap), va="top", color=INK2, fontsize=9)
    ax.set_ylabel("처치 - 통제")
    ax.set_xlabel("주")
    for a in axes:
        a.axvline(n_pre - 0.5, color=INK2, lw=1)
        a.grid(axis="y")
        a.set_axisbelow(True)
    axes[0].text(n_pre - 0.3, axes[0].get_ylim()[0], " 광고 시작", va="bottom", color=INK2, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "geo_pretrend.png", dpi=150)
    plt.close(fig)

    n_ctrl_cells = panel.loc[(panel["treated"] == 0) & (panel["post"] == 1)].shape[0]
    return res, pre, n_ctrl_cells


# ---------------------------------------------------------------- 3. MMM
def run_mmm():
    spend = mmm.simulate_spend()
    weekly, true_betas = mmm.simulate_sales(spend, TRUE_PARAMS, TRUE_ROI)
    weekly.to_csv(DATA / "mmm_weekly.csv", index=False)
    fit = mmm.fit_mmm(weekly)
    roi = mmm.channel_roi(weekly, fit)
    roi["true_roi"] = roi["channel"].map(TRUE_ROI)

    print("\n[3] MMM, {}주, R2 {:.3f}".format(len(weekly), fit["r2"]))
    for c in mmm.CHANNELS:
        print("  {:<6} 추정 모수 {} / 정답 {}".format(c, fit["params"][c], TRUE_PARAMS[c]))
    print(roi.round(2).to_string(index=False))

    # 채널이 같이 움직이는 경우: 같은 정답, 다른 광고비 패턴
    spend_c = mmm.simulate_spend(correlated=True)
    weekly_c, _ = mmm.simulate_sales(spend_c, TRUE_PARAMS, TRUE_ROI)
    fit_c = mmm.fit_mmm(weekly_c)
    roi_c = mmm.channel_roi(weekly_c, fit_c)
    corr = spend_c.corr().values[np.triu_indices(3, 1)]
    print("  [같이 움직이는 경우] 채널 간 상관 {:.2f}~{:.2f}, R2 {:.3f}".format(
        corr.min(), corr.max(), fit_c["r2"]))
    print("  ROI " + ", ".join("{} {:.2f}".format(c, r) for c, r in zip(roi_c["channel"], roi_c["roi"])))

    # 시드를 바꿔 같은 일을 50번: 추정치가 얼마나 흔들리나
    spread = []
    for seed in range(50):
        sp = mmm.simulate_spend(seed=100 + seed)
        wk, _ = mmm.simulate_sales(sp, TRUE_PARAMS, TRUE_ROI, seed=200 + seed)
        spread.append(mmm.channel_roi(wk, mmm.fit_mmm(wk))["roi"].values)
    spread = np.array(spread)
    print("  [시드 50개] ROI 5~95% 범위: " + ", ".join(
        "{} {:.2f}~{:.2f}".format(c, *np.percentile(spread[:, i], [5, 95]))
        for i, c in enumerate(mmm.CHANNELS)))

    # 반응 곡선과 예산 재배분 (정상 상태, 매주 같은 금액을 쓴다고 가정)
    true_curves = {c: (TRUE_PARAMS[c][0], TRUE_PARAMS[c][1] * mmm.adstock(spend[c], TRUE_PARAMS[c][0]).mean(),
                       TRUE_PARAMS[c][2], true_betas[c]) for c in mmm.CHANNELS}
    fit_curves = mmm.curve_params(fit["params"], fit["betas"], fit["adstock_mean"])
    budget = {c: spend[c].mean() for c in mmm.CHANNELS}
    m_fit = mmm.marginal_roi(budget, fit_curves)
    m_true = mmm.marginal_roi(budget, true_curves)
    src = min(m_fit, key=m_fit.get)
    dst = max(m_fit, key=m_fit.get)
    new_budget = mmm.reallocate(budget, src, dst, 0.3)
    gain_fit = mmm.total_response(new_budget, fit_curves) - mmm.total_response(budget, fit_curves)
    gain_true = mmm.total_response(new_budget, true_curves) - mmm.total_response(budget, true_curves)
    moved = budget[src] * 0.3
    print("  한계 ROI(추정): " + ", ".join("{} {:.2f}".format(c, m_fit[c]) for c in mmm.CHANNELS))
    print("  한계 ROI(정답): " + ", ".join("{} {:.2f}".format(c, m_true[c]) for c in mmm.CHANNELS))
    print("  재배분: {} 예산 30% ({:.1f}/주)를 {}로 -> 주간 매출 추정 +{:.1f}, 정답 +{:.1f} 백만 원".format(
        src, moved, dst, gain_fit, gain_true))

    realloc = pd.DataFrame([{
        "옮긴 채널": LABEL[src], "받은 채널": LABEL[dst], "옮긴 금액(백만 원/주)": round(moved, 1),
        "주간 매출 변화 추정": round(gain_fit, 1), "주간 매출 변화 정답": round(gain_true, 1)}])
    save_table(realloc, "mmm_reallocation")
    mtable = pd.DataFrame({
        "채널": [LABEL[c] for c in mmm.CHANNELS],
        "정답 ROI": [TRUE_ROI[c] for c in mmm.CHANNELS],
        "추정 ROI": roi["roi"].round(2).values,
        "시드 50개 5~95%": ["{:.2f}~{:.2f}".format(*np.percentile(spread[:, i], [5, 95]))
                          for i in range(3)],
        "같이 움직일 때 추정 ROI": roi_c["roi"].round(2).values,
        "한계 ROI 추정": [round(m_fit[c], 2) for c in mmm.CHANNELS],
        "한계 ROI 정답": [round(m_true[c], 2) for c in mmm.CHANNELS],
    })
    save_table(mtable, "mmm_roi")

    plot_mmm_fit(weekly, fit)
    plot_response(spend, budget, true_curves, fit_curves)
    plot_roi_compare(roi, roi_c)
    return roi, roi_c, spread, (src, dst, moved, gain_fit, gain_true)


def plot_mmm_fit(weekly, fit):
    t = np.arange(len(weekly))
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    ax = axes[0]
    ax.plot(t, weekly["sales"], color=GRAY, lw=1.5, label="실제 매출")
    ax.plot(t, fit["fitted"], color=BLUE, lw=2, label="모델 적합")
    ax.set_ylabel("주간 매출 (백만 원)")
    ax.set_title("MMM 적합: 기본 수요 + 채널 3개", loc="left", color=INK)
    ax.legend(frameon=False, loc="upper left", ncol=2)
    ax = axes[1]
    bottom = np.zeros(len(t))
    for c in mmm.CHANNELS:
        part = fit["betas"][c] * mmm.transform(weekly[c].values, *fit["params"][c])
        ax.fill_between(t, bottom, bottom + part, color=COLOR[c], lw=0, label=LABEL[c])
        bottom = bottom + part
    ax.set_ylabel("채널 기여 추정 (백만 원)")
    ax.set_xlabel("주")
    ax.legend(frameon=False, loc="upper left", ncol=3)
    for a in axes:
        a.grid(axis="y")
        a.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "mmm_decomposition.png", dpi=150)
    plt.close(fig)


def plot_response(spend, budget, true_curves, fit_curves):
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    for ax, c in zip(axes, mmm.CHANNELS):
        x = np.linspace(0, spend[c].max() * 1.3, 200)
        ax.plot(x, mmm.response(x, *true_curves[c]), color=GRAY, lw=2, ls="--", label="정답")
        ax.plot(x, mmm.response(x, *fit_curves[c]), color=COLOR[c], lw=2, label="추정")
        ax.axvline(budget[c], color=INK2, lw=1)
        ax.text(budget[c], ax.get_ylim()[1] * 0.02, " 현재 평균", color=INK2, fontsize=9)
        ax.set_title(LABEL[c], loc="left", color=INK)
        ax.set_xlabel("주간 광고비 (백만 원)")
        ax.grid(axis="y")
        ax.set_axisbelow(True)
        ax.legend(frameon=False, loc="upper left")
    axes[0].set_ylabel("주간 기여 매출 (백만 원)")
    fig.suptitle("반응 곡선: 검색은 이미 평평하고, 소셜은 아직 오르는 구간", x=0.01, ha="left", color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "mmm_response_curves.png", dpi=150)
    plt.close(fig)


def plot_roi_compare(roi, roi_c):
    x = np.arange(3)
    w = 0.26
    fig, ax = plt.subplots(figsize=(7, 3.8))
    series = [("정답", [TRUE_ROI[c] for c in mmm.CHANNELS], INK2),
              ("추정 (채널이 따로 움직임)", roi["roi"].values, BLUE),
              ("추정 (채널이 같이 움직임)", roi_c["roi"].values, ORANGE)]
    for i, (name, vals, col) in enumerate(series):
        bars = ax.bar(x + (i - 1) * w, vals, width=w - 0.03, color=col, label=name)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.04, "{:.2f}".format(v),
                    ha="center", color=INK, fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([LABEL[c] for c in mmm.CHANNELS])
    ax.set_ylabel("평균 ROI")
    ax.set_title("채널 예산이 같이 움직이면 MMM이 효과를 잘못 나눈다", loc="left", color=INK)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.set_ylim(0, max(max(s[1]) for s in series) * 1.25)
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "mmm_roi_compare.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- 결론 표
def summary_table(lift_out, geo_out, mmm_out):
    l_res, l_true, l_table, holdout_cost = lift_out
    g_res, _, n_ctrl_cells = geo_out
    roi, roi_c, spread, _ = mmm_out
    ci = "{:.2f} ({:.2f}~{:.2f})"
    rows = [
        ("마지막 클릭 기여", "소셜", "{:.2f}".format(l_table["ROAS"].iloc[1]), "{:.2f}".format(l_true),
         "거의 없음 (매일 나옴)", "소재, 입찰 같은 일상 운영의 상대 비교"),
        ("유저 홀드아웃", "소셜", ci.format(l_res["iroas"], *l_res["iroas_ci"]), "{:.2f}".format(l_true),
         "홀드아웃 {:,}명의 증분 매출 약 {:,.0f}만 원 포기".format(l_res["n_holdout"], holdout_cost / 1e4),
         "유저 단위로 노출을 막을 수 있는 채널의 예산 판단"),
        ("지역 실험 (DID)", "TV", ci.format(g_res["iroas"], *g_res["iroas_ci"]), "{:.2f}".format(TRUE_ROI["tv"]),
         "통제 지역 x 주 {}칸 광고 중단, 지역 수가 적으면 구간이 넓다".format(n_ctrl_cells),
         "TV, 옥외처럼 사람 단위로 못 막는 채널"),
    ]
    for i, c in enumerate(mmm.CHANNELS):
        rows.append(("MMM", LABEL[c],
                     "{:.2f} (시드 50개 5~95%: {:.2f}~{:.2f})".format(
                         roi["roi"].iloc[i], *np.percentile(spread[:, i], [5, 95])),
                     "{:.2f}".format(TRUE_ROI[c]),
                     "주간 데이터 2~3년, 실험 비용 없음",
                     "채널 전체 예산 배분, 실험으로 보정한 뒤"))
    for i, c in enumerate(mmm.CHANNELS):
        rows.append(("MMM (채널이 같이 움직임)", LABEL[c], "{:.2f}".format(roi_c["roi"].iloc[i]),
                     "{:.2f}".format(TRUE_ROI[c]), "같음", "이 상태로는 채널 분리에 쓰지 않는다"))
    out = pd.DataFrame(rows, columns=["방법", "채널", "추정 ROI (괄호: 구간)", "정답", "비용", "언제 쓰나"])
    save_table(out, "summary")
    print("\n[결론 표]")
    print(out.iloc[:, :4].to_string(index=False))


def main():
    lift_out = run_lift()
    geo_out = run_geo()
    mmm_out = run_mmm()
    summary_table(lift_out, geo_out, mmm_out)


if __name__ == "__main__":
    main()
