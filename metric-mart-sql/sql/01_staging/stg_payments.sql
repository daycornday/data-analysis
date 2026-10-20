-- stg_payments | grain: payment_id 1행 = 결제 시도 1건 (가장 늦게 적재된 상태를 채택)
DROP TABLE IF EXISTS stg_payments;
CREATE TABLE stg_payments AS
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY payment_id ORDER BY ingested_at DESC) AS rn
    FROM raw_payments
)
SELECT
    payment_id,
    CAST(user_id AS INTEGER)                               AS user_id,
    datetime(replace(replace(paid_at, 'T', ' '), 'Z', '')) AS paid_at,
    lower(trim(plan))                                      AS plan,
    CAST(replace(amount, ',', '') AS INTEGER)              AS amount,
    lower(trim(status))                                    AS status
FROM ranked
WHERE rn = 1;
