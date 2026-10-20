-- dim_users | grain: user_id 1행 = 가입자 1명 (가입 속성 + 첫 결제 시각)
DROP TABLE IF EXISTS dim_users;
CREATE TABLE dim_users AS
WITH first_paid AS (
    SELECT user_id, min(paid_at) AS first_paid_at
    FROM stg_payments
    WHERE status = 'paid'
    GROUP BY user_id
)
SELECT
    u.user_id,
    u.signup_at,
    u.signup_date,
    date(u.signup_date, 'weekday 0', '-6 days') AS signup_week,
    strftime('%Y-%m', u.signup_date)            AS signup_month,
    u.channel,
    u.country,
    f.first_paid_at
FROM stg_users u
LEFT JOIN first_paid f ON f.user_id = u.user_id;
