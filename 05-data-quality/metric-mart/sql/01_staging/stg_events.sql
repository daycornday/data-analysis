-- stg_events | grain: event_id 1행 = 로그인 유저의 이벤트 1건 (재전송 중복 제거, 익명 제외)
DROP TABLE IF EXISTS stg_events;
CREATE TABLE stg_events AS
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY ingested_at) AS rn
    FROM raw_events
    WHERE user_id IS NOT NULL
)
SELECT
    event_id,
    CAST(user_id AS INTEGER)                                AS user_id,
    lower(trim(event_name))                                 AS event_name,
    datetime(replace(replace(event_at, 'T', ' '), 'Z', '')) AS event_at
FROM ranked
WHERE rn = 1;
