"""합성 원천 테이블: users, events, orders, channels.

- users: 테스트 계정이 섞여 있고, 유입 채널이 비어 있는(NULL) 유저가 있다
- events: 방문 로그. 한 유저가 하루에 여러 번 방문할 수 있다 (fan-out의 재료)
- orders: 방문한 날에만 주문이 생긴다. 주문 시각은 하루 중 아무 때나
- channels: 채널 이름 목록(룩업 테이블). NULL 채널은 여기에 없다
"""
import datetime as dt

import numpy as np

CHANNELS = ["검색", "SNS", "추천"]
FIRST_DAY = dt.date(2026, 8, 25)
LAST_DAY = dt.date(2026, 10, 5)


def _ts(day, seconds):
    return (dt.datetime.combine(day, dt.time()) + dt.timedelta(seconds=int(seconds))).strftime("%Y-%m-%d %H:%M:%S")


def make_source(conn, seed=20261020, n_users=2000):
    """conn(sqlite3)에 원천 테이블 네 개를 만든다."""
    rng = np.random.default_rng(seed)
    days = [FIRST_DAY + dt.timedelta(d) for d in range((LAST_DAY - FIRST_DAY).days + 1)]

    users, events, orders = [], [], []
    for uid in range(1, n_users + 1):
        is_test = int(rng.random() < 0.03)
        channel = None if rng.random() < 0.08 else CHANNELS[rng.integers(len(CHANNELS))]
        users.append((uid, channel, is_test))
        visit_p = rng.uniform(0.02, 0.3)
        for day in days:
            if rng.random() >= visit_p:
                continue
            for _ in range(rng.integers(1, 4)):  # 하루 1~3회 방문
                events.append((uid, "visit", _ts(day, rng.integers(0, 86400))))
            if rng.random() < 0.08:
                amount = int(rng.integers(5, 120)) * 1000
                orders.append((uid, _ts(day, rng.integers(0, 86400)), amount))

    cur = conn.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS users;    DROP TABLE IF EXISTS events;
        DROP TABLE IF EXISTS orders;   DROP TABLE IF EXISTS channels;
        CREATE TABLE users (user_id INTEGER PRIMARY KEY, channel TEXT, is_test INTEGER);
        CREATE TABLE events (event_id INTEGER PRIMARY KEY, user_id INTEGER, event_name TEXT, event_ts TEXT);
        CREATE TABLE orders (order_id INTEGER PRIMARY KEY, user_id INTEGER, order_ts TEXT, amount INTEGER);
        CREATE TABLE channels (channel TEXT PRIMARY KEY);
    """)
    cur.executemany("INSERT INTO users VALUES (?, ?, ?)", users)
    cur.executemany("INSERT INTO events (user_id, event_name, event_ts) VALUES (?, ?, ?)", events)
    cur.executemany("INSERT INTO orders (user_id, order_ts, amount) VALUES (?, ?, ?)", orders)
    cur.executemany("INSERT INTO channels VALUES (?)", [(c,) for c in CHANNELS])
    cur.execute("DROP TABLE IF EXISTS ref_daily")
    cur.execute("CREATE TABLE ref_daily (dt TEXT PRIMARY KEY, orders INTEGER, revenue INTEGER)")
    cur.executemany("INSERT INTO ref_daily VALUES (?, ?, ?)", reference_daily(users, orders))
    conn.commit()


def reference_daily(users, orders):
    """외부 기준 수치 역할: SQL 마트와 따로, 파이썬으로 원천 행을 직접 세어 만든 9월 일별 주문 수와 매출.

    '다른 팀이 독립적으로 산출한 수치'나 '운영 대시보드 결과'를 흉내 낸다.
    """
    test_users = {uid for uid, _, is_test in users if is_test}
    daily = {}
    for uid, ts, amount in orders:
        day = ts[:10]
        if uid in test_users or not day.startswith("2026-09"):
            continue
        cnt, rev = daily.get(day, (0, 0))
        daily[day] = (cnt + 1, rev + amount)
    return [(day, cnt, rev) for day, (cnt, rev) in sorted(daily.items())]
