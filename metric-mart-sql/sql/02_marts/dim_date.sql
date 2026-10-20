-- dim_date | grain: date_day 1행 = 달력 하루 (첫 가입일부터 마지막 이벤트, 결제일까지 빈 날 없이)
DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date AS
WITH RECURSIVE days(date_day) AS (
    SELECT min(signup_date) FROM stg_users
    UNION ALL
    SELECT date(date_day, '+1 day')
    FROM days
    WHERE date_day < (
        SELECT max(last_day) FROM (
            SELECT max(date(event_at)) AS last_day FROM stg_events
            UNION ALL
            SELECT max(date(paid_at)) FROM stg_payments
        )
    )
)
SELECT
    date_day,
    date(date_day, 'weekday 0', '-6 days') AS week_start,
    strftime('%Y-%m', date_day)            AS month,
    CAST(strftime('%w', date_day) AS INTEGER) AS day_of_week
FROM days;
