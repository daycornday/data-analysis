"""데이터 테스트가 정상 데이터에선 통과하고, 일부러 깨뜨린 데이터에선 실패하는지 확인한다."""
from metric_mart_sql import checks, pipeline


def test_all_checks_pass_on_clean_build(built):
    results = checks.run_all(built)
    assert results["passed"].all(), results[~results["passed"]]


def test_unique_fails_on_duplicate_key(built):
    built.execute("INSERT INTO dim_users SELECT * FROM dim_users LIMIT 1")
    assert checks.unique(built, "dim_users", "user_id") == 1


def test_not_null_fails_on_missing_amount(built):
    built.execute("UPDATE fct_orders SET amount = NULL WHERE rowid IN (SELECT rowid FROM fct_orders LIMIT 3)")
    assert checks.not_null(built, "fct_orders", "amount") == 3


def test_relationships_fails_on_orphan_order(built):
    built.execute("""
        INSERT INTO fct_orders (order_id, user_id, ordered_at, order_date, plan, amount, status)
        VALUES ('p_orphan', 999999, '2026-01-10 00:00:00', '2026-01-10', 'monthly', 9900, 'paid')""")
    assert checks.relationships(built, "fct_orders", "user_id", "dim_users", "user_id") == 1


def test_row_count_fails_on_join_fanout(built):
    # dim_users에 중복 키가 생기면 fct_orders를 다시 만들 때 결제 행이 불어난다
    first_payer = built.execute("SELECT user_id FROM stg_payments LIMIT 1").fetchone()[0]
    built.execute("INSERT INTO dim_users SELECT * FROM dim_users WHERE user_id = ?", (first_payer,))
    pipeline.run_model(built, "fct_orders")
    n_payments = built.execute(
        "SELECT count(*) FROM stg_payments WHERE user_id = ?", (first_payer,)).fetchone()[0]
    assert checks.row_count_preserved(built, "stg_payments", "fct_orders") == n_payments


def test_sum_reconcile_fails_when_metric_drops_rows(built):
    built.execute("DELETE FROM metric_arppu WHERE month = (SELECT min(month) FROM metric_arppu)")
    gap = checks.sums_match(built, "SELECT sum(revenue) FROM metric_arppu",
                            "SELECT sum(amount) FROM fct_orders WHERE status = 'paid'")
    assert gap > 0


def test_sum_reconcile_fails_when_dau_is_inflated(built):
    built.execute("UPDATE metric_daily_active SET dau = dau + 1 WHERE date_day = (SELECT min(date_day) FROM dim_date)")
    results = checks.run_all(built).set_index("test")
    assert not results.loc["sum dau: metric_daily_active = fct_events(user, day)", "passed"]


def test_run_all_reports_failures(built):
    built.execute("INSERT INTO fct_events SELECT * FROM fct_events LIMIT 1")
    results = checks.run_all(built).set_index("test")
    assert not results.loc["unique fct_events.event_id", "passed"]
    assert not results.loc["row_count stg_events = fct_events", "passed"]
    assert results["passed"].sum() == len(results) - 2
