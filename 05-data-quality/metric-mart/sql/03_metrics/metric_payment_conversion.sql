-- metric_payment_conversion | grain: signup_month 1행 = 가입 월 코호트 (가입 후 14일 창을 다 본 유저만)
DROP TABLE IF EXISTS metric_payment_conversion;
CREATE TABLE metric_payment_conversion AS
WITH eligible AS (
    SELECT
        signup_month,
        CASE
            WHEN first_paid_at IS NOT NULL
             AND julianday(date(first_paid_at)) - julianday(signup_date) <= 13 THEN 1
            ELSE 0
        END AS converted
    FROM dim_users
    WHERE signup_date <= date((SELECT max(date_day) FROM dim_date), '-13 days')
)
SELECT
    signup_month,
    count(*)                                  AS signups,
    sum(converted)                            AS converted_14d,
    round(1.0 * sum(converted) / count(*), 4) AS conversion_rate_14d
FROM eligible
GROUP BY signup_month
ORDER BY signup_month;
