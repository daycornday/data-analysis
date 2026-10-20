"""마트 네 개를 버그 버전과 고친 버전으로 만든다. 집계 기간은 2026년 9월 한 달.

| 마트 | 심은 버그 |
|---|---|
| mart_orders          | 조인 fan-out: 같은 날 방문 로그와 조인해 주문이 방문 횟수만큼 복제됨 |
| mart_channel_revenue | NULL 누락: 채널 룩업과 INNER JOIN 해서 채널이 NULL인 유저 매출이 빠짐 |
| mart_daily           | 기간 경계: 타임스탬프에 BETWEEN '09-01' AND '09-30'을 써서 9/30 00:00 이후가 빠짐 |
| mart_kpi             | 분모 모집단 불일치(전체 가입자) + 정수 나눗셈(전환율이 0) |
"""

BUGGY = {
    "mart_orders": """
        CREATE TABLE mart_orders AS
        SELECT o.order_id, o.user_id, o.order_ts, o.amount,
               1 AS visited_that_day
        FROM orders o
        JOIN events e
          ON e.user_id = o.user_id
         AND DATE(e.event_ts) = DATE(o.order_ts)
         AND e.event_name = 'visit'
    """,
    "mart_channel_revenue": """
        CREATE TABLE mart_channel_revenue AS
        SELECT c.channel, SUM(o.amount) AS revenue
        FROM orders o
        JOIN users u    ON u.user_id = o.user_id
        JOIN channels c ON c.channel = u.channel
        WHERE o.order_ts >= '2026-09-01' AND o.order_ts < '2026-10-01'
          AND u.is_test = 0
        GROUP BY c.channel
    """,
    "mart_daily": """
        CREATE TABLE mart_daily AS
        SELECT DATE(o.order_ts) AS dt, COUNT(*) AS orders, SUM(o.amount) AS revenue
        FROM orders o
        JOIN users u ON u.user_id = o.user_id
        WHERE o.order_ts BETWEEN '2026-09-01' AND '2026-09-30'
          AND u.is_test = 0
        GROUP BY DATE(o.order_ts)
    """,
    "mart_kpi": """
        CREATE TABLE mart_kpi AS
        SELECT b.buyers, v.visitors, b.buyers / v.visitors AS cvr
        FROM (SELECT COUNT(DISTINCT o.user_id) AS buyers
              FROM orders o JOIN users u ON u.user_id = o.user_id
              WHERE o.order_ts >= '2026-09-01' AND o.order_ts < '2026-10-01'
                AND u.is_test = 0) b,
             (SELECT COUNT(*) AS visitors FROM users) v
    """,
}

FIXED = {
    "mart_orders": """
        CREATE TABLE mart_orders AS
        SELECT o.order_id, o.user_id, o.order_ts, o.amount,
               CASE WHEN EXISTS (SELECT 1 FROM events e
                                 WHERE e.user_id = o.user_id
                                   AND DATE(e.event_ts) = DATE(o.order_ts)
                                   AND e.event_name = 'visit')
                    THEN 1 ELSE 0 END AS visited_that_day
        FROM orders o
    """,
    "mart_channel_revenue": """
        CREATE TABLE mart_channel_revenue AS
        SELECT COALESCE(u.channel, '미분류') AS channel, SUM(o.amount) AS revenue
        FROM orders o
        JOIN users u ON u.user_id = o.user_id
        WHERE o.order_ts >= '2026-09-01' AND o.order_ts < '2026-10-01'
          AND u.is_test = 0
        GROUP BY COALESCE(u.channel, '미분류')
    """,
    "mart_daily": """
        CREATE TABLE mart_daily AS
        SELECT DATE(o.order_ts) AS dt, COUNT(*) AS orders, SUM(o.amount) AS revenue
        FROM orders o
        JOIN users u ON u.user_id = o.user_id
        WHERE o.order_ts >= '2026-09-01' AND o.order_ts < '2026-10-01'
          AND u.is_test = 0
        GROUP BY DATE(o.order_ts)
    """,
    "mart_kpi": """
        CREATE TABLE mart_kpi AS
        SELECT b.buyers, v.visitors, 1.0 * b.buyers / v.visitors AS cvr
        FROM (SELECT COUNT(DISTINCT o.user_id) AS buyers
              FROM orders o JOIN users u ON u.user_id = o.user_id
              WHERE o.order_ts >= '2026-09-01' AND o.order_ts < '2026-10-01'
                AND u.is_test = 0) b,
             (SELECT COUNT(DISTINCT e.user_id) AS visitors
              FROM events e JOIN users u ON u.user_id = e.user_id
              WHERE e.event_name = 'visit'
                AND e.event_ts >= '2026-09-01' AND e.event_ts < '2026-10-01'
                AND u.is_test = 0) v
    """,
}


def build_marts(conn, version):
    """version = 'buggy' 또는 'fixed'. 에러 없이 끝나면 V0(돌아감)는 통과한 셈이다."""
    sqls = {"buggy": BUGGY, "fixed": FIXED}[version]
    for name, sql in sqls.items():
        conn.execute("DROP TABLE IF EXISTS " + name)
        conn.execute(sql)
    conn.commit()
    return list(sqls)
