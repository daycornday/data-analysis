-- metric_arppu | grain: month 1행 = 결제 월 (status = 'paid'만, 환불과 실패 제외)
DROP TABLE IF EXISTS metric_arppu;
CREATE TABLE metric_arppu AS
SELECT
    strftime('%Y-%m', order_date)                         AS month,
    sum(amount)                                           AS revenue,
    count(DISTINCT user_id)                               AS paying_users,
    count(*)                                              AS paid_orders,
    round(1.0 * sum(amount) / count(DISTINCT user_id), 0) AS arppu
FROM fct_orders
WHERE status = 'paid'
GROUP BY strftime('%Y-%m', order_date)
ORDER BY month;
