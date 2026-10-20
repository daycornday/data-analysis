"""버그를 심은 마트와 고친 마트에 같은 검사를 돌려, 검사가 버그를 잡고 레벨이 어떻게 갈리는지 보여 준다."""
import sqlite3
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "src"))
from analysis_validation_kit import make_source, build_marts, run_suite, summarize_levels  # noqa: E402

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

SEED = 20261020
TABLE_NAMES = {
    "mart_orders": "주문 마트",
    "mart_channel_revenue": "채널별 매출",
    "mart_daily": "일별 매출",
    "mart_kpi": "전환율 KPI",
}


def build(version):
    path = HERE / "data" / "mart_{}.sqlite".format(version)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    make_source(conn, SEED)
    build_marts(conn, version)
    print("[{}] 빌드 완료: 에러 없음 (V0)".format(version))
    return conn


def headline(conn):
    """보고서에 실릴 숫자들."""
    q = lambda sql: conn.execute(sql).fetchone()  # noqa: E731
    rows, amount = q("SELECT COUNT(*), SUM(amount) FROM mart_orders")
    channel_rev, = q("SELECT SUM(revenue) FROM mart_channel_revenue")
    daily_rev, days = q("SELECT SUM(revenue), COUNT(*) FROM mart_daily")
    buyers, visitors, cvr = q("SELECT buyers, visitors, cvr FROM mart_kpi")
    return {"주문 마트 행 수": rows, "주문 마트 금액 합": amount, "채널별 매출 합": channel_rev,
            "일별 매출 합": daily_rev, "일별 마트 일수": days,
            "구매자": buyers, "분모(방문자)": visitors, "전환율": cvr}


def plot_matrix(buggy, fixed, path):
    labels = ["{} / {} ({})".format(TABLE_NAMES[t], c, lv)
              for t, c, lv in zip(buggy["table"], buggy["check"], buggy["level"])]
    fig, ax = plt.subplots(figsize=(9, 6))
    n = len(labels)
    for col, df in enumerate([buggy, fixed]):
        for row, ok in enumerate(df["passed"]):
            color = "#4c956c" if ok else "#c8553d"
            ax.add_patch(plt.Rectangle((col, n - 1 - row), 0.95, 0.9, color=color))
            ax.text(col + 0.475, n - 1 - row + 0.45, "통과" if ok else "실패",
                    ha="center", va="center", color="white", fontsize=10)
    ax.set_xlim(0, 2)
    ax.set_ylim(0, n)
    ax.set_xticks([0.475, 1.475])
    ax.set_xticklabels(["버그 심은 마트", "고친 마트"])
    ax.set_yticks([n - 1 - i + 0.45 for i in range(n)])
    ax.set_yticklabels(labels, fontsize=9)
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_title("같은 검사 11개를 두 마트에 돌린 결과 (괄호는 검사가 올려 주는 레벨)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def write_card(per_table, doc_level, fixed, path):
    lines = ["[검증 카드]  레벨: {}   대상: 고친 마트 4개".format(doc_level), ""]
    lines.append("- 마트별 레벨 : " + ", ".join("{} {}".format(TABLE_NAMES[t], lv) for t, lv in per_table.items()))
    lines.append("- 문서 레벨   : 가장 낮은 마트를 따라 {}".format(doc_level))
    lines.append("- 대조 기준   : 원천 orders, events, users 테이블 / 외부 기준 ref_daily (9월 일별 주문 수, 매출)")
    lines.append("- 결과        : 검사 {}개 중 {}개 통과".format(len(fixed), int(fixed["passed"].sum())))
    lines.append("- 미검증      : 채널별 매출과 전환율은 합계, 분모 한 숫자만 외부와 맞춤(채널 단위 셀 대조 안 함). "
                 "9월 이외 기간. 지표 정의 자체가 맞는지는 검사 범위 밖")
    lines.append("- 재현 방법   : python run.py")
    lines.append("- 검증자      : 자동 검사")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))


def main():
    (HERE / "data").mkdir(exist_ok=True)
    out = HERE / "outputs"
    out.mkdir(exist_ok=True)

    conns = {v: build(v) for v in ["buggy", "fixed"]}
    print("\n[핵심 숫자: 버그 / 고침]")
    hb, hf = headline(conns["buggy"]), headline(conns["fixed"])
    for k in hb:
        fmt = (lambda x: "{:.4f}".format(x)) if k == "전환율" else (lambda x: "{:,}".format(x))
        print("  {}: {} / {}".format(k, fmt(hb[k]), fmt(hf[k])))

    results = {}
    for v, conn in conns.items():
        res = run_suite(conn)
        results[v] = res
        per_table, doc_level = summarize_levels(res)
        print("\n[{}] 검사 결과: {}/{} 통과".format(v, int(res["passed"].sum()), len(res)))
        for r in res.itertuples():
            print("  {:<5} {:<20} {:<8} {}  {}".format("통과" if r.passed else "실패", r.table, r.check, r.level, r.detail))
        print("  마트별 레벨: {}, 문서 레벨: {}".format(per_table, doc_level))

    both = results["buggy"][["table", "check", "level"]].copy()
    both["buggy_passed"] = results["buggy"]["passed"]
    both["buggy_detail"] = results["buggy"]["detail"]
    both["fixed_passed"] = results["fixed"]["passed"]
    both["fixed_detail"] = results["fixed"]["detail"]
    both.to_csv(out / "check_results.csv", index=False, encoding="utf-8-sig")

    plot_matrix(results["buggy"], results["fixed"], out / "check_matrix.png")
    per_table, doc_level = summarize_levels(results["fixed"])
    write_card(per_table, doc_level, results["fixed"], out / "validation_card.md")

    for conn in conns.values():
        conn.close()


if __name__ == "__main__":
    main()
