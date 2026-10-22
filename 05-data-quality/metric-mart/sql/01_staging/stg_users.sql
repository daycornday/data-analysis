-- stg_users | grain: user_id 1행 = 가입자 1명 (재적재 중복 제거)
DROP TABLE IF EXISTS stg_users;
CREATE TABLE stg_users AS
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ingested_at DESC) AS rn
    FROM raw_users
    WHERE user_id IS NOT NULL
)
SELECT
    CAST(user_id AS INTEGER)                                 AS user_id,
    datetime(replace(replace(signup_at, 'T', ' '), 'Z', '')) AS signup_at,
    date(replace(replace(signup_at, 'T', ' '), 'Z', ''))     AS signup_date,
    lower(trim(channel))                                     AS channel,
    upper(trim(country))                                     AS country
FROM ranked
WHERE rn = 1;
