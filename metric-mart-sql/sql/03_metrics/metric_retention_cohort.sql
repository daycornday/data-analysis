-- metric_retention_cohort | grain: (signup_week, week_n) 1행 = 가입 주 코호트의 가입 후 n주차 (관측이 끝난 칸만)
DROP TABLE IF EXISTS metric_retention_cohort;
CREATE TABLE metric_retention_cohort AS
WITH cohorts AS (
    SELECT signup_week, count(*) AS cohort_size, max(signup_date) AS last_signup
    FROM dim_users
    GROUP BY signup_week
),
user_weeks AS (
    SELECT DISTINCT
        u.signup_week,
        e.user_id,
        e.days_since_signup / 7 AS week_n
    FROM fct_events e
    JOIN dim_users u ON u.user_id = e.user_id
    WHERE e.days_since_signup BETWEEN 0 AND 62
),
retained AS (
    SELECT signup_week, week_n, count(*) AS active_users
    FROM user_weeks
    GROUP BY signup_week, week_n
)
SELECT
    c.signup_week,
    r.week_n,
    c.cohort_size,
    r.active_users,
    round(1.0 * r.active_users / c.cohort_size, 4) AS retention_rate
FROM cohorts c
JOIN retained r ON r.signup_week = c.signup_week
WHERE date(c.last_signup, '+' || (7 * r.week_n + 6) || ' days')
      <= (SELECT max(date_day) FROM dim_date)
ORDER BY c.signup_week, r.week_n;
