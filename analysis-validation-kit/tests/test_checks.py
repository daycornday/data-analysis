"""버그 있는 마트는 해당 검사에서 실패하고, 고친 마트는 모든 검사를 통과해야 한다."""
import sqlite3

import pandas as pd

from analysis_validation_kit import (
    run_suite, summarize_levels, table_level,
    check_key_unique, check_row_count, check_ratio, check_period, check_full_reconcile,
)


def _passed(results, table, check):
    row = results[(results["table"] == table) & (results["check"] == check)]
    assert len(row) == 1
    return bool(row["passed"].iloc[0])


def test_fixed_mart_passes_everything(fixed):
    res = run_suite(fixed)
    assert res["passed"].all(), res[~res["passed"]].to_string()


def test_fanout_caught_by_rowcount_key_and_sum(buggy):
    res = run_suite(buggy)
    assert not _passed(res, "mart_orders", "키 유일성")
    assert not _passed(res, "mart_orders", "행 수 보존")
    assert not _passed(res, "mart_orders", "합계 대조")


def test_null_channel_caught_by_sum(buggy):
    res = run_suite(buggy)
    assert _passed(res, "mart_channel_revenue", "키 유일성")  # 키는 멀쩡하다
    assert not _passed(res, "mart_channel_revenue", "합계 대조")


def test_period_boundary_caught(buggy):
    res = run_suite(buggy)
    assert not _passed(res, "mart_daily", "경계 확인")
    assert not _passed(res, "mart_daily", "전수 대조")


def test_denominator_and_integer_division_caught(buggy):
    res = run_suite(buggy)
    assert not _passed(res, "mart_kpi", "분모 정의 확인")
    assert not _passed(res, "mart_kpi", "비율 계산 확인")


def test_levels_buggy_v0_fixed_v2(buggy, fixed):
    _, doc_buggy = summarize_levels(run_suite(buggy))
    per_table, doc_fixed = summarize_levels(run_suite(fixed))
    assert doc_buggy == "V0"
    assert doc_fixed == "V2"
    assert per_table["mart_daily"] == "V3"


def _toy():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE t (k INTEGER, dt TEXT, n INTEGER, d INTEGER, r REAL);
        INSERT INTO t VALUES (1, '2026-09-01', 1, 4, 0.25), (2, '2026-09-02', 1, 4, 0.25),
                             (2, '2026-09-03', 1, 4, 0);
        CREATE TABLE src (k INTEGER);
        INSERT INTO src VALUES (1), (2);
        CREATE TABLE ref (dt TEXT, n INTEGER);
        INSERT INTO ref VALUES ('2026-09-01', 1), ('2026-09-02', 1), ('2026-09-03', 2);
    """)
    return conn


def test_key_unique_known_answer():
    res = check_key_unique(_toy(), "t", ["k"])
    assert not res["passed"] and "1개" in res["detail"]


def test_row_count_known_answer():
    assert not check_row_count(_toy(), "t", "SELECT COUNT(*) FROM src")["passed"]


def test_ratio_known_answer():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE k AS SELECT 3 AS n, 4 AS d, 3 / 4 AS r")
    assert not check_ratio(conn, "k", "n", "d", "r")["passed"]
    conn.execute("CREATE TABLE k2 AS SELECT 3 AS n, 4 AS d, 1.0 * 3 / 4 AS r")
    assert check_ratio(conn, "k2", "n", "d", "r")["passed"]


def test_period_known_answer():
    conn = _toy()
    assert check_period(conn, "t", "dt", "2026-09-01", "2026-09-03")["passed"]
    assert not check_period(conn, "t", "dt", "2026-09-01", "2026-09-04")["passed"]


def test_full_reconcile_known_answer():
    res = check_full_reconcile(_toy(), "t", "ref", "dt", ["n"])
    assert not res["passed"] and "2026-09-03" in res["detail"]


def test_table_level_stops_at_first_failure():
    checks = pd.DataFrame({"level": ["V1", "V2", "V3"], "passed": [True, False, True]})
    assert table_level(checks) == "V1"
    checks = pd.DataFrame({"level": ["V1", "V2"], "passed": [True, True]})
    assert table_level(checks) == "V2"
