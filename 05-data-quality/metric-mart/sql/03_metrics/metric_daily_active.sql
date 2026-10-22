-- metric_daily_active | grain: date_day 1행 = 하루 (이벤트가 없는 날도 0으로 남긴다)
DROP TABLE IF EXISTS metric_daily_active;
CREATE TABLE metric_daily_active AS
WITH active AS (
    SELECT event_date, count(DISTINCT user_id) AS dau
    FROM fct_events
    GROUP BY event_date
),
signups AS (
    SELECT signup_date, count(*) AS new_users
    FROM dim_users
    GROUP BY signup_date
)
SELECT
    d.date_day,
    coalesce(a.dau, 0)       AS dau,
    coalesce(s.new_users, 0) AS new_users
FROM dim_date d
LEFT JOIN active a  ON a.event_date = d.date_day
LEFT JOIN signups s ON s.signup_date = d.date_day
ORDER BY d.date_day;
