"""데이터 테스트 (dbt test의 unique, not_null, relationships에 해당).

각 함수는 '위반 건수'를 돌려준다. 0이면 통과다.
"""
import pandas as pd


def _scalar(conn, sql):
    value = conn.execute(sql).fetchone()[0]
    return 0 if value is None else value


def unique(conn, table, column):
    """같은 키가 두 번 이상 나온 키 값의 개수."""
    return _scalar(conn, f"""
        SELECT count(*) FROM (
            SELECT {column} FROM {table} GROUP BY {column} HAVING count(*) > 1
        )""")


def not_null(conn, table, column):
    """NULL인 행 수."""
    return _scalar(conn, f"SELECT count(*) FROM {table} WHERE {column} IS NULL")


def relationships(conn, child, column, parent, parent_column):
    """자식 테이블의 키 중 부모에 없는 행 수 (참조 무결성)."""
    return _scalar(conn, f"""
        SELECT count(*) FROM {child} c
        LEFT JOIN {parent} p ON p.{parent_column} = c.{column}
        WHERE c.{column} IS NOT NULL AND p.{parent_column} IS NULL""")


def row_count_preserved(conn, source, target):
    """조인 전후 행 수 차이의 절댓값. fan-out이나 누락이 있으면 0이 아니다."""
    n_source = _scalar(conn, f"SELECT count(*) FROM {source}")
    n_target = _scalar(conn, f"SELECT count(*) FROM {target}")
    return abs(n_source - n_target)


def sums_match(conn, metric_sql, source_sql):
    """지표 테이블의 합계와 원천 팩트의 합계 차이의 절댓값."""
    return abs(_scalar(conn, metric_sql) - _scalar(conn, source_sql))


def check_list():
    """(이름, 함수, 인자) 목록. 새 테스트는 여기에 한 줄 추가한다."""
    return [
        ("unique dim_users.user_id", unique, ("dim_users", "user_id")),
        ("unique dim_date.date_day", unique, ("dim_date", "date_day")),
        ("unique fct_orders.order_id", unique, ("fct_orders", "order_id")),
        ("unique fct_events.event_id", unique, ("fct_events", "event_id")),
        ("not_null dim_users.signup_date", not_null, ("dim_users", "signup_date")),
        ("not_null fct_orders.user_id", not_null, ("fct_orders", "user_id")),
        ("not_null fct_orders.amount", not_null, ("fct_orders", "amount")),
        ("not_null fct_events.user_id", not_null, ("fct_events", "user_id")),
        ("relationships fct_orders.user_id -> dim_users", relationships,
         ("fct_orders", "user_id", "dim_users", "user_id")),
        ("relationships fct_events.user_id -> dim_users", relationships,
         ("fct_events", "user_id", "dim_users", "user_id")),
        ("relationships fct_events.event_date -> dim_date", relationships,
         ("fct_events", "event_date", "dim_date", "date_day")),
        ("row_count stg_users = dim_users", row_count_preserved, ("stg_users", "dim_users")),
        ("row_count stg_payments = fct_orders", row_count_preserved, ("stg_payments", "fct_orders")),
        ("row_count stg_events = fct_events", row_count_preserved, ("stg_events", "fct_events")),
        ("sum revenue: metric_arppu = fct_orders(paid)", sums_match,
         ("SELECT sum(revenue) FROM metric_arppu",
          "SELECT sum(amount) FROM fct_orders WHERE status = 'paid'")),
        ("sum dau: metric_daily_active = fct_events(user, day)", sums_match,
         ("SELECT sum(dau) FROM metric_daily_active",
          "SELECT count(*) FROM (SELECT DISTINCT user_id, event_date FROM fct_events)")),
        ("sum new_users: metric_daily_active = dim_users", sums_match,
         ("SELECT sum(new_users) FROM metric_daily_active",
          "SELECT count(*) FROM dim_users")),
    ]


def run_all(conn):
    """모든 테스트를 돌려 이름, 위반 건수, 통과 여부 표를 돌려준다."""
    rows = []
    for name, func, args in check_list():
        failures = func(conn, *args)
        rows.append({"test": name, "failures": failures, "passed": failures == 0})
    return pd.DataFrame(rows)
