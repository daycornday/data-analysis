-- fct_orders | grain: order_id 1행 = 결제 시도 1건 (실패, 환불 포함, status로 구분)
DROP TABLE IF EXISTS fct_orders;
CREATE TABLE fct_orders AS
SELECT
    p.payment_id   AS order_id,
    p.user_id,
    p.paid_at      AS ordered_at,
    date(p.paid_at) AS order_date,
    p.plan,
    p.amount,
    p.status,
    CAST(julianday(date(p.paid_at)) - julianday(u.signup_date) AS INTEGER) AS days_since_signup,
    CASE WHEN p.status = 'paid' AND p.paid_at = u.first_paid_at THEN 1 ELSE 0 END AS is_first_paid
FROM stg_payments p
LEFT JOIN dim_users u ON u.user_id = p.user_id;
