# 리뷰 예시

## 문제
`users(user_id, signup_date)`, `orders(order_id, user_id, order_date, amount)`가 있다.
가입 월별로 "가입 후 30일 안에 첫 구매를 한 사용자 비율"을 구하라.

grain 메모 (쿼리를 보기 전에 적는다)
- 결과 한 행 = 가입 월 하나
- 분모 = 그 달 가입자 전원 (구매 안 한 사람 포함)
- 30일 조건 = 사용자별 첫 구매일과 가입일의 차이

## 받은 답안

```sql
SELECT strftime('%Y-%m', u.signup_date) AS signup_month,
       COUNT(DISTINCT o.user_id) / COUNT(u.user_id) AS conv_rate
FROM users u
JOIN orders o ON u.user_id = o.user_id
WHERE julianday(o.order_date) - julianday(u.signup_date) <= 30
GROUP BY 1;
```

## 점수

| 항목 | 점수 | 이유 |
|------|------|------|
| 정답 | 0 / 4 | 아래 오류 세 개가 모두 수치를 바꾼다 |
| grain | 0 / 2 | 분모가 가입자가 아니라 30일 안 주문 행이다 |
| 효율 | 2 / 2 | 스캔은 한 번이다 |
| 실무 자연스러움 | 1.5 / 2 | 짧고 읽기 쉽다. 비율 계산을 CTE로 나누면 검증이 쉬워진다 |

## 수치가 달라지는 오류

1. **분모가 주문 행 수다.** INNER JOIN 뒤 `COUNT(u.user_id)`는 주문 한 건마다 한 번씩 센다. 30일 안에 3번 산 사용자는 분모에 3으로 들어간다. 구매 안 한 가입자는 아예 빠진다. 고치기: 가입자 CTE에서 분모를 따로 센다.
2. **정수 나눗셈.** 정수끼리 나누면 결과가 0이나 1로만 나온다. 고치기: `1.0 *`을 곱한다.
3. **첫 구매가 아니라 아무 구매나 본다.** 지금 조건은 "30일 안에 주문이 하나라도 있으면"이다. 문제와 결과가 같아 보이지만, 가입 전 주문 데이터가 섞이면 음수 차이도 통과한다. 고치기: 첫 구매일을 먼저 구하고 0일 이상 30일 이하로 건다.

## 잘한 점
- 날짜 차이를 일 단위로 정확히 계산했다
- GROUP BY 기준이 결과 grain과 같다

## 모범 답안

```sql
WITH first_orders AS (
    -- 첫 구매는 전체 기간에서 구한다. 기간을 먼저 자르면 첫 구매가 바뀐다
    SELECT user_id, MIN(order_date) AS first_order_date
    FROM orders
    GROUP BY user_id
),
signups AS (
    SELECT u.user_id,
           strftime('%Y-%m', u.signup_date) AS signup_month,
           julianday(f.first_order_date) - julianday(u.signup_date) AS days_to_first
    FROM users u
    -- LEFT JOIN: 구매 안 한 가입자도 분모에 남겨야 한다
    LEFT JOIN first_orders f ON u.user_id = f.user_id
)
SELECT signup_month,
       COUNT(*) AS signups,
       SUM(CASE WHEN days_to_first BETWEEN 0 AND 30 THEN 1 ELSE 0 END) AS converted,
       -- 1.0을 곱해 정수 나눗셈을 피한다
       1.0 * SUM(CASE WHEN days_to_first BETWEEN 0 AND 30 THEN 1 ELSE 0 END) / COUNT(*) AS conv_rate
FROM signups
GROUP BY signup_month
ORDER BY signup_month;
```

## 실무 연결
분모가 주문 행이 되면 재구매가 많은 달일수록 전환율이 낮아 보인다. 좋은 달이 나쁜 달로 보고되는 오류라서, 월별 추이 대시보드에서 특히 위험하다.
