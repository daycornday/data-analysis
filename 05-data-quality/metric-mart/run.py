"""원본 생성 -> staging -> marts -> metrics -> 데이터 테스트 -> 결과 저장.

폴더 안에서 `python run.py`로 실행한다.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "src"))

from metric_mart_sql import checks, pipeline, synth  # noqa: E402

DATA = HERE / "data"
OUT = HERE / "outputs"
SEED = 42
N_USERS = 2000

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


def layer_row_counts(conn):
    tables = ["raw_users", "raw_payments", "raw_events", "stg_users", "stg_payments",
              "stg_events", "dim_users", "dim_date", "fct_orders", "fct_events"]
    rows = [{"table": t, "rows": conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]} for t in tables]
    return pd.DataFrame(rows)


def plot_dau(dau):
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(pd.to_datetime(dau["date_day"]), dau["dau"], color="#2a6fdb", linewidth=2)
    ax.set_title("일간 활성 유저 (DAU)")
    ax.set_xlabel("날짜")
    ax.set_ylabel("활성 유저 수")
    ax.grid(axis="y", color="#e5e5e5")
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "dau.png", dpi=120)
    plt.close(fig)


def plot_retention(retention):
    grid = retention.pivot(index="signup_week", columns="week_n", values="retention_rate")
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(grid.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(grid.shape[1]))
    ax.set_xticklabels(grid.columns)
    ax.set_yticks(range(grid.shape[0]))
    ax.set_yticklabels(grid.index)
    ax.set_title("가입 주 코호트 주차별 리텐션")
    ax.set_xlabel("가입 후 주차 (week_n)")
    ax.set_ylabel("가입 주 (월요일 시작)")
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            value = grid.values[i, j]
            if pd.notna(value):
                ax.text(j, i, f"{value:.0%}", ha="center", va="center", fontsize=7,
                        color="white" if value > 0.55 else "#222222")
    fig.colorbar(im, ax=ax, label="리텐션")
    fig.tight_layout()
    fig.savefig(OUT / "retention_cohort.png", dpi=120)
    plt.close(fig)


def main():
    DATA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)

    raw = synth.make_raw(n_users=N_USERS, seed=SEED)
    for name, df in raw.items():
        df.to_csv(DATA / f"{name}.csv", index=False)

    conn = pipeline.connect()
    pipeline.load_raw(conn, raw)
    built = pipeline.build(conn)
    print("만든 모델:", ", ".join(built))

    counts = layer_row_counts(conn)
    counts.to_csv(OUT / "layer_row_counts.csv", index=False)
    print(counts.to_string(index=False))

    results = checks.run_all(conn)
    results.to_csv(OUT / "data_tests.csv", index=False)
    print(f"\n데이터 테스트 {int(results['passed'].sum())}/{len(results)} 통과")
    if not results["passed"].all():
        print(results[~results["passed"]].to_string(index=False))

    metrics = {}
    for name in ["metric_daily_active", "metric_payment_conversion",
                 "metric_retention_cohort", "metric_arppu"]:
        metrics[name] = pd.read_sql(f"SELECT * FROM {name}", conn)
        metrics[name].to_csv(OUT / f"{name}.csv", index=False)

    dau = metrics["metric_daily_active"]
    print(f"\nDAU 평균 {dau['dau'].mean():.1f}, 최대 {dau['dau'].max()}")
    print("\n14일 결제 전환율\n" + metrics["metric_payment_conversion"].to_string(index=False))
    print("\nARPPU\n" + metrics["metric_arppu"].to_string(index=False))
    retention = metrics["metric_retention_cohort"]
    avg = retention.groupby("week_n")["retention_rate"].mean().round(4)
    print("\n주차별 평균 리텐션 (코호트 단순 평균)\n" + avg.to_string())

    plot_dau(dau)
    plot_retention(retention)
    return 0 if results["passed"].all() else 1


if __name__ == "__main__":
    sys.exit(main())
