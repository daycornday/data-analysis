"""마트마다 어떤 검사를 돌릴지, 결과로 검증 레벨을 어떻게 매길지."""
import pandas as pd

from .checks import (
    check_row_count, check_key_unique, check_sum_matches,
    check_denominator, check_ratio, check_period, check_full_reconcile,
)

LEVELS = ["V0", "V1", "V2", "V3"]

# 지표 정의서에서 옮긴 기준. 마트 쿼리가 아니라 원천 테이블과 외부 기준(ref_daily)을 읽는다
RAW_ORDER_COUNT = "SELECT COUNT(*) FROM orders"
RAW_ORDER_AMOUNT = "SELECT SUM(amount) FROM orders"
REF_SEP_REVENUE = "SELECT SUM(revenue) FROM ref_daily"
VISITOR_DEFINITION = """
    SELECT COUNT(DISTINCT e.user_id)
    FROM events e JOIN users u ON u.user_id = e.user_id
    WHERE e.event_name = 'visit' AND u.is_test = 0
      AND e.event_ts >= '2026-09-01' AND e.event_ts < '2026-10-01'
"""


def run_suite(conn):
    """마트 네 개에 검사를 돌려 결과 표를 돌려준다."""
    results = [
        check_key_unique(conn, "mart_orders", ["order_id"]),
        check_row_count(conn, "mart_orders", RAW_ORDER_COUNT),
        check_sum_matches(conn, "mart_orders", "SELECT SUM(amount) FROM mart_orders",
                          RAW_ORDER_AMOUNT, "전체 주문 금액"),

        check_key_unique(conn, "mart_channel_revenue", ["channel"]),
        check_sum_matches(conn, "mart_channel_revenue", "SELECT SUM(revenue) FROM mart_channel_revenue",
                          REF_SEP_REVENUE, "채널 합 vs 9월 매출"),

        check_key_unique(conn, "mart_daily", ["dt"]),
        check_period(conn, "mart_daily", "dt", "2026-09-01", "2026-09-30"),
        check_sum_matches(conn, "mart_daily", "SELECT SUM(revenue) FROM mart_daily",
                          REF_SEP_REVENUE, "일별 합 vs 9월 매출"),
        check_full_reconcile(conn, "mart_daily", "ref_daily", "dt", ["orders", "revenue"]),

        check_ratio(conn, "mart_kpi", "buyers", "visitors", "cvr"),
        check_denominator(conn, "mart_kpi", "SELECT visitors FROM mart_kpi",
                          "SELECT buyers FROM mart_kpi", VISITOR_DEFINITION),
    ]
    return pd.DataFrame(results)


def table_level(checks):
    """V0(빌드가 돌아감)에서 시작해, 그 레벨 이하 검사가 전부 통과한 가장 높은 레벨.

    어떤 레벨의 검사가 하나도 없으면 그 위로는 올라가지 않는다.
    """
    level = "V0"
    for lv in LEVELS[1:]:
        at_lv = checks[checks["level"] == lv]
        if at_lv.empty or not at_lv["passed"].all():
            break
        level = lv
    return level


def summarize_levels(results):
    """마트별 레벨과 문서 전체 레벨(가장 낮은 마트를 따른다)."""
    per_table = {t: table_level(g) for t, g in results.groupby("table", sort=False)}
    doc = min(per_table.values(), key=LEVELS.index)
    return per_table, doc
