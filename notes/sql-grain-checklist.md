# SQL 쓰기 전 grain 체크리스트

> 쿼리가 틀리는 이유의 대부분은 문법이 아니라 "행 하나가 무엇인가"를 정하지 않고 쓰기 시작한 데 있다.

## 1. grain을 먼저 한 줄로 적는다

결과 테이블의 행 하나가 무엇인지 문장으로 적고 시작한다.

```sql
-- grain: (가입 월, 채널) 1행
-- grain: 유저 1명 1행
-- grain: 주문 1건 1행
```

- 입력 테이블마다 grain을 확인한다. 주문 테이블이 "주문 1건 1행"인지 "주문 상품 1개 1행"인지에 따라 `count(*)`의 뜻이 바뀐다.
- 키가 정말 유일한지 쿼리로 확인한다.

```sql
SELECT order_id, count(*) FROM orders GROUP BY order_id HAVING count(*) > 1;
```

## 2. 분모 모집단을 정한다

비율 지표는 분자보다 분모에서 더 자주 틀린다.

- 분모는 "기회가 있었던 사람"이다. 14일 전환율이면 가입 후 14일이 다 지난 사람만 넣는다.
- 분자는 분모의 부분집합이어야 한다. 분자에만 있는 사람(분모 조건에서 빠진 사람)이 섞이면 비율이 부풀려진다.
- 0건인 사람도 분모에 남아야 한다. 이벤트 테이블에서 출발하면 행동하지 않은 사람이 사라진다. 유저 테이블에서 출발해 LEFT JOIN 한다.

```sql
-- 가입 후 14일 전환율. 분모 = 14일 창을 다 본 가입자
SELECT
    count(*)                                         AS signups,
    sum(CASE WHEN o.user_id IS NOT NULL THEN 1 ELSE 0 END) AS converted
FROM users u
LEFT JOIN (
    SELECT DISTINCT o.user_id
    FROM orders o
    JOIN users u2 ON u2.user_id = o.user_id
    WHERE o.status = 'paid'
      AND o.order_date <= date(u2.signup_date, '+13 days')
) o ON o.user_id = u.user_id
WHERE u.signup_date <= date('now', '-14 days');
```

## 3. 집계 누락을 막는다

- `SELECT`에 있는데 `GROUP BY`에 없는 컬럼이 있으면 일부 DB는 아무 값이나 골라 준다(SQLite, 옛 MySQL). 에러가 나지 않으니 더 위험하다.
- 날짜별 집계는 데이터가 없는 날이 행째로 빠진다. 날짜 테이블에 LEFT JOIN 해서 0을 남긴다.
- `count(column)`은 NULL을 세지 않는다. `count(*)`와 다르다는 것을 알고 고른다.
- `WHERE`에 LEFT JOIN 오른쪽 테이블 조건을 걸면 INNER JOIN이 된다. 그 조건은 `ON`으로 옮긴다.

```sql
-- 잘못: 쿠폰을 안 쓴 주문이 사라진다
SELECT o.order_id, c.code FROM orders o LEFT JOIN coupons c ON c.order_id = o.order_id
WHERE c.type = 'welcome';

-- 바르게
SELECT o.order_id, c.code FROM orders o
LEFT JOIN coupons c ON c.order_id = o.order_id AND c.type = 'welcome';
```

## 4. 조인 fan-out을 의심한다

1:N 조인 뒤에 N쪽이 아닌 값을 `sum`하면 값이 N배가 된다.

```sql
-- 잘못: 주문에 상품이 3개면 배송비가 3번 더해진다
SELECT sum(o.shipping_fee)
FROM orders o
JOIN order_items i ON i.order_id = o.order_id;

-- 바르게: 합칠 grain을 먼저 맞추고 조인한다
SELECT sum(shipping_fee) FROM orders;
```

- 조인 전후 행 수를 비교한다. 늘었다면 의도한 것인지 설명할 수 있어야 한다.
- 차원 테이블 키가 유일하지 않으면 1:1이라고 믿은 조인이 1:N이 된다.
- 두 개의 N쪽 테이블(주문 상품, 결제 내역)을 한 번에 붙이면 N x M이 된다. 각각 먼저 집계해서 1행으로 만든 뒤 붙인다.

## 5. 정수 나눗셈

정수끼리 나누면 소수점이 버려진다. 전환율이 전부 0으로 나온다면 이것부터 본다.

```sql
SELECT 169 / 687;          -- 0   (SQLite, PostgreSQL, SQL Server)
SELECT 1.0 * 169 / 687;    -- 0.246
SELECT CAST(169 AS REAL) / 687;
```

- MySQL의 `/`는 소수를 돌려주지만 `DIV`는 정수 나눗셈이다. DB마다 다르니 쓰는 DB에서 한 번 확인한다.
- 분모가 0이면 에러나 NULL이 나온다. `NULLIF(분모, 0)`로 막는다.

## 쓰기 전 체크리스트

- [ ] 결과의 grain을 한 줄로 적었다
- [ ] 입력 테이블마다 grain과 키 유일성을 확인했다
- [ ] 분모가 "기회가 있었던 모집단"이고, 분자가 그 부분집합이다
- [ ] 0건인 대상이 행째로 사라지지 않는다 (출발 테이블, 날짜 스파인)
- [ ] LEFT JOIN 오른쪽 조건을 WHERE에 두지 않았다
- [ ] 조인 전후 행 수를 비교했고, 늘었다면 설명할 수 있다
- [ ] 비율 계산에 `1.0 *` 또는 CAST가 있고, 분모 0을 막았다
- [ ] 결과 합계를 원천 테이블 합계와 한 번 대조했다
