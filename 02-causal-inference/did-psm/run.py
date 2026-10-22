"""DID(장기기증 등록 정책)와 PSM(NSW 직업훈련)을 공개 데이터로 재현한다.

실행: python run.py  (이 폴더 안에서)
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

from causal_inference.did import did_table, did_regression, pre_trend_slopes, event_study  # noqa: E402
from causal_inference.psm import psm_att, balance_table  # noqa: E402

DATA = HERE / "data"
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

BLUE = "#2a78d6"    # 처치군
ORANGE = "#eb6834"  # 대조군
GRAY = "#8a8985"

QUARTERS = ["Q42010", "Q12011", "Q22011", "Q32011", "Q42011", "Q12012"]
QUARTER_LABELS = ["10Q4", "11Q1", "11Q2", "11Q3", "11Q4", "12Q1"]
POLICY_QUARTER = 4  # 2011년 3분기부터 정책 후


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- DID
def load_organ():
    df = pd.read_csv(DATA / "organ_donations.csv")
    df["Quarter_Num"] = df["Quarter"].map({q: i + 1 for i, q in enumerate(QUARTERS)})
    df["Treated"] = (df["State"] == "California").astype(int)
    df["Post"] = (df["Quarter_Num"] >= POLICY_QUARTER).astype(int)
    return df


def run_did():
    df = load_organ()
    table, did = did_table(df, "Rate", "Treated", "Post")
    fit = did_regression(df, "Rate", "Treated", "Post", cluster="State")
    slopes = pre_trend_slopes(df, "Rate", "Treated", "Quarter_Num", POLICY_QUARTER - 1)
    means = df.groupby(["Quarter_Num", "Treated"])["Rate"].mean().unstack("Treated")
    gaps = means[1] - means[0]
    es = event_study(df, "Rate", "State", "Quarter_Num", "Treated",
                     ref_time=POLICY_QUARTER - 1, cluster="State")

    table.index = ["대조군(다른 26개 주)", "처치군(캘리포니아)"]
    table.round(4).to_csv(OUT / "did_2x2.csv", encoding="utf-8-sig")
    es.round(4).to_csv(OUT / "did_event_study.csv", index=False)

    plot_did_trends(means)
    plot_event_study(es)

    return {
        "n_states": df["State"].nunique(),
        "table": table,
        "did": did,
        "coef": fit.params["Treated:Post"],
        "se": fit.bse["Treated:Post"],
        "p": fit.pvalues["Treated:Post"],
        "slopes": slopes,
        "pre_gaps": gaps.loc[: POLICY_QUARTER - 1].values,
        "es": es,
    }


def plot_did_trends(means):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = means.index.values
    ax.plot(x, means[0], color=ORANGE, linewidth=2, marker="o", markersize=7, label="다른 26개 주 평균")
    ax.plot(x, means[1], color=BLUE, linewidth=2, marker="o", markersize=7, label="캘리포니아")
    ax.axvline(POLICY_QUARTER - 0.5, color=GRAY, linestyle="--", linewidth=1)
    ax.text(POLICY_QUARTER - 0.45, 0.36, "정책 시행\n(2011년 3분기)", color="#52514e", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(QUARTER_LABELS)
    ax.set_ylim(0.2, 0.5)
    ax.set_xlabel("분기")
    ax.set_ylabel("기증 등록 동의율")
    ax.set_title("분기별 장기기증 등록률: 캘리포니아와 다른 주")
    ax.legend(frameon=False, loc="center left")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(OUT / "did_trends.png", dpi=150)
    plt.close(fig)


def plot_event_study(es):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    k = es["k"].values
    err = [es["coef"] - es["ci_low"], es["ci_high"] - es["coef"]]
    ax.axhline(0, color=GRAY, linewidth=1)
    ax.axvline(-0.5, color=GRAY, linestyle="--", linewidth=1)
    ax.errorbar(k, es["coef"], yerr=err, fmt="o", color=BLUE, markersize=8,
                elinewidth=2, capsize=4)
    ax.text(-1, -0.003, "기준 (k = -1)", ha="center", va="top", fontsize=9, color="#52514e")
    ax.set_xticks(k)
    ax.set_xlabel("정책 시행 기준 상대 분기 (k)")
    ax.set_ylabel("캘리포니아 - 다른 주 차이 (기준 대비)")
    ax.set_title("이벤트 스터디: 분기별 효과와 95% 신뢰구간")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(OUT / "did_event_study.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- PSM
COVARIATES = ["age", "educ", "black", "marr", "nodegree", "re74", "re75"]

# 공변량 구성에 따라 추정치가 얼마나 흔들리는지 보는 사양들
SPECS = [
    ("기본 7개 (원고 균형표의 변수)", COVARIATES, False),
    ("기본 7개 + hisp", COVARIATES + ["hisp"], False),
    ("기본 7개 + 제곱항, 무소득 더미", COVARIATES, True),
    ("기본 7개 + hisp + 제곱항, 무소득 더미", COVARIATES + ["hisp"], True),
]


def load_nsw():
    nsw = pd.read_csv(DATA / "nsw_mixtape.csv")
    cps = pd.read_csv(DATA / "cps_mixtape.csv")
    observational = pd.concat([nsw[nsw["treat"] == 1], cps], ignore_index=True)
    return nsw, observational


def add_flexible_terms(df):
    df = df.copy()
    df["age_sq"] = df["age"] ** 2
    df["educ_sq"] = df["educ"] ** 2
    df["u74"] = (df["re74"] == 0).astype(int)
    df["u75"] = (df["re75"] == 0).astype(int)
    return df


def run_psm():
    nsw, obs = load_nsw()
    experimental = (nsw.loc[nsw["treat"] == 1, "re78"].mean()
                    - nsw.loc[nsw["treat"] == 0, "re78"].mean())
    naive = (obs.loc[obs["treat"] == 1, "re78"].mean()
             - obs.loc[obs["treat"] == 0, "re78"].mean())

    att, treated, control, matched = psm_att(obs, "treat", "re78", COVARIATES)
    balance = balance_table(treated, control, matched, COVARIATES)
    balance.round(3).to_csv(OUT / "psm_balance.csv", index=False)

    spec_rows = []
    flexible = add_flexible_terms(obs)
    for name, covs, flex in SPECS:
        cols = covs + (["age_sq", "educ_sq", "u74", "u75"] if flex else [])
        spec_att = psm_att(flexible, "treat", "re78", cols)[0]
        spec_rows.append({"spec": name, "att": spec_att})
    specs = pd.DataFrame(spec_rows)
    specs.round(0).to_csv(OUT / "psm_specs.csv", index=False, encoding="utf-8-sig")

    plot_ps_distribution(treated, control)
    plot_love(balance)

    return {
        "n_treated": len(treated),
        "n_control": len(control),
        "n_unique_matched": matched.index.nunique(),
        "experimental": experimental,
        "naive": naive,
        "att": att,
        "balance": balance,
        "specs": specs,
    }


def plot_ps_distribution(treated, control):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bins = np.linspace(0, 0.6, 31)
    ax.hist(control["ps"], bins=bins, histtype="step", color=ORANGE, linewidth=2,
            label="CPS 대조군 ({:,}명)".format(len(control)))
    ax.hist(treated["ps"], bins=bins, histtype="step", color=BLUE, linewidth=2,
            label="훈련 참가자 ({}명)".format(len(treated)))
    ax.set_yscale("log")
    ax.set_xlabel("성향점수 (훈련에 참가할 추정 확률)")
    ax.set_ylabel("인원 (로그 축)")
    ax.set_title("매칭 전 성향점수 분포")
    ax.legend(frameon=False)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(OUT / "psm_ps_distribution.png", dpi=150)
    plt.close(fig)


def plot_love(balance):
    order = balance.reindex(balance["smd_before"].abs().sort_values().index)
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.axvspan(-0.1, 0.1, color="#e4e3df", alpha=0.7, linewidth=0)
    ax.axvline(0, color=GRAY, linewidth=1)
    ax.scatter(order["smd_before"], y, color=ORANGE, s=60, label="매칭 전", zorder=3,
               edgecolor="white", linewidth=1.5)
    ax.scatter(order["smd_after"], y, color=BLUE, s=60, label="매칭 후", zorder=3,
               edgecolor="white", linewidth=1.5)
    ax.set_yticks(y)
    ax.set_yticklabels(order["covariate"])
    ax.set_xlabel("표준화 평균 차이 (SMD), 회색 띠 = |SMD| < 0.1")
    ax.set_title("공변량 균형 점검 (love plot)")
    ax.legend(frameon=False, loc="lower right")
    style_axes(ax)
    ax.grid(axis="x", color="#e4e3df", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(OUT / "psm_love_plot.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- 출력
def write_summary(d, p):
    t = d["table"]
    lines = [
        "# 결과 요약 (run.py 자동 생성)",
        "",
        "## DID: 캘리포니아 능동적 선택 정책",
        "",
        "| 집단 | 정책 전 | 정책 후 | 전후 변화 |",
        "|---|---|---|---|",
    ]
    for name, row in t.iterrows():
        lines.append("| {} | {:.4f} | {:.4f} | {:+.4f} |".format(
            name, row["before"], row["after"], row["change"]))
    lines += [
        "",
        "- 2x2 DID: {:+.4f}".format(d["did"]),
        "- 회귀 Treated:Post: {:+.4f} (클러스터 SE {:.4f}, p = {:.4f})".format(
            d["coef"], d["se"], d["p"]),
        "- 정책 전 분기당 기울기: 캘리포니아 {:+.4f}, 다른 주 {:+.4f}".format(
            d["slopes"][1], d["slopes"][0]),
        "- 정책 전 분기별 격차: " + ", ".join("{:+.3f}".format(g) for g in d["pre_gaps"]),
        "",
        "| k | 계수 | 95% CI |",
        "|---|---|---|",
    ]
    for _, row in d["es"].iterrows():
        lines.append("| {} | {:+.4f} | [{:+.4f}, {:+.4f}] |".format(
            int(row["k"]), row["coef"], row["ci_low"], row["ci_high"]))
    lines += [
        "",
        "## PSM: NSW 직업훈련 (처치 {}명, CPS 대조 {}명)".format(p["n_treated"], p["n_control"]),
        "",
        "| 방법 | ATT (1978년 소득, 달러) |",
        "|---|---|",
        "| 실험 정답 | {:+,.0f} |".format(p["experimental"]),
        "| 단순 관측 비교 | {:+,.0f} |".format(p["naive"]),
        "| PSM 1:1 최근접 | {:+,.0f} |".format(p["att"]),
        "",
        "- 매칭에 쓰인 서로 다른 대조군: {}명".format(p["n_unique_matched"]),
        "",
        "| 공변량 | 매칭 전 SMD | 매칭 후 SMD |",
        "|---|---|---|",
    ]
    for _, row in p["balance"].iterrows():
        lines.append("| {} | {:+.3f} | {:+.3f} |".format(
            row["covariate"], row["smd_before"], row["smd_after"]))
    lines += ["", "| 성향점수 모델 | ATT |", "|---|---|"]
    for _, row in p["specs"].iterrows():
        lines.append("| {} | {:+,.0f} |".format(row["spec"], row["att"]))
    text = "\n".join(lines) + "\n"
    (OUT / "results.md").write_text(text, encoding="utf-8")
    return text


def main():
    d = run_did()
    p = run_psm()
    print(write_summary(d, p))


if __name__ == "__main__":
    main()
