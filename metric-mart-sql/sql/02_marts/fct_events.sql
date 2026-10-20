-- fct_events | grain: event_id 1행 = 로그인 유저의 이벤트 1건
DROP TABLE IF EXISTS fct_events;
CREATE TABLE fct_events AS
SELECT
    e.event_id,
    e.user_id,
    e.event_name,
    e.event_at,
    date(e.event_at) AS event_date,
    CAST(julianday(date(e.event_at)) - julianday(u.signup_date) AS INTEGER) AS days_since_signup
FROM stg_events e
LEFT JOIN dim_users u ON u.user_id = e.user_id;
