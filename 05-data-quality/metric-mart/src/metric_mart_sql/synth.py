"""합성 원본 데이터 생성.

구독형 서비스를 흉내 낸 원본 3개(유저, 결제, 이벤트)를 만든다.
원본은 일부러 지저분하다. 모든 값은 문자열이고, 같은 행이 두 번 적재되기도 하며,
시각 형식이 섞여 있고, 대소문자와 공백이 제각각이다. staging이 이것을 정리한다.
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

START = datetime(2026, 1, 1)
N_DAYS = 90
CHANNELS = ["organic", "paid_search", "referral"]
COUNTRIES = ["kr", "jp", "us"]
PLANS = {"monthly": 9900, "annual": 99000}


def _fmt_ts(ts, rng):
    """시각 문자열. 30%는 ISO 형식(T, Z)으로 섞는다."""
    if rng.random() < 0.3:
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def _messy(text, rng):
    """대소문자와 앞뒤 공백을 흐트러뜨린다."""
    r = rng.random()
    if r < 0.15:
        return " " + text.upper()
    if r < 0.3:
        return text.capitalize() + " "
    return text


def _random_time(day, rng):
    return day + timedelta(seconds=int(rng.integers(0, 86400)))


def make_users(n_users, rng):
    rows = []
    for uid in range(1, n_users + 1):
        day = START + timedelta(days=int(rng.integers(0, N_DAYS)))
        signup_at = _random_time(day, rng)
        rows.append({
            "user_id": str(uid),
            "signup_at": _fmt_ts(signup_at, rng),
            "channel": _messy(str(rng.choice(CHANNELS, p=[0.5, 0.3, 0.2])), rng),
            "country": _messy(str(rng.choice(COUNTRIES, p=[0.7, 0.2, 0.1])), rng),
            "ingested_at": signup_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    users = pd.DataFrame(rows)
    # 2%는 같은 유저가 한 번 더 적재된다 (재적재)
    dup = users.sample(frac=0.02, random_state=int(rng.integers(1e6)))
    return pd.concat([users, dup], ignore_index=True)


def _activity_days(signup_day, propensity, rng):
    """가입 후 활동한 날짜 오프셋 목록. 가입일은 항상 활동한다."""
    last = N_DAYS - 1 - signup_day
    days = [0]
    for d in range(1, last + 1):
        p = propensity * (0.1 + 0.9 * np.exp(-d / 7))
        if rng.random() < p:
            days.append(d)
    return days


def make_events_and_payments(users, rng):
    users = users.drop_duplicates("user_id")
    events, payments = [], []
    eid, pid = 0, 0
    for row in users.itertuples():
        signup_at = datetime.strptime(row.signup_at.replace("T", " ").replace("Z", ""),
                                      "%Y-%m-%d %H:%M:%S")
        signup_day = (signup_at.date() - START.date()).days
        propensity = rng.beta(2, 3)
        for offset in _activity_days(signup_day, propensity, rng):
            day = START + timedelta(days=signup_day + offset)
            n_views = int(rng.poisson(2))
            for name in ["session_start"] + ["view_item"] * n_views:
                eid += 1
                ts = signup_at if offset == 0 and name == "session_start" else _random_time(day, rng)
                events.append([f"e{eid:07d}", row.user_id, name, ts])

        # 결제: 활동 성향이 높을수록 전환 확률이 높다
        if rng.random() < 0.15 + 0.4 * propensity:
            first = signup_day + int(rng.geometric(0.12)) - 1
            plan = "annual" if rng.random() < 0.2 else "monthly"
            pay_day = first
            while pay_day < N_DAYS:
                if rng.random() < 0.05:  # 카드 실패 후 같은 날 재시도
                    pid += 1
                    payments.append([f"p{pid:06d}", row.user_id, _random_time(START + timedelta(days=pay_day), rng),
                                     plan, PLANS[plan], "failed"])
                pid += 1
                status = "refunded" if rng.random() < 0.04 else "paid"
                payments.append([f"p{pid:06d}", row.user_id, _random_time(START + timedelta(days=pay_day), rng),
                                 plan, PLANS[plan], status])
                if plan == "annual" or rng.random() > 0.8:
                    break
                pay_day += 30
    return events, payments


def _events_frame(events, rng):
    rows = []
    for event_id, user_id, name, ts in events:
        ingested = ts + timedelta(seconds=int(rng.integers(1, 120)))
        rows.append([event_id, user_id, name, _fmt_ts(ts, rng), ingested.strftime("%Y-%m-%d %H:%M:%S")])
        if rng.random() < 0.03:  # 클라이언트 재전송으로 같은 이벤트가 한 번 더 들어온다
            late = ingested + timedelta(seconds=int(rng.integers(5, 600)))
            rows.append([event_id, user_id, name, _fmt_ts(ts, rng), late.strftime("%Y-%m-%d %H:%M:%S")])
    n_anon = len(events) // 50  # 로그인 전 익명 이벤트
    for i in range(n_anon):
        ts = _random_time(START + timedelta(days=int(rng.integers(0, N_DAYS))), rng)
        rows.append([f"a{i:07d}", None, "view_item", _fmt_ts(ts, rng), ts.strftime("%Y-%m-%d %H:%M:%S")])
    cols = ["event_id", "user_id", "event_name", "event_at", "ingested_at"]
    return pd.DataFrame(rows, columns=cols)


def _payments_frame(payments, rng):
    rows = []
    for payment_id, user_id, ts, plan, amount, status in payments:
        amount_text = f"{amount:,}" if rng.random() < 0.2 else str(amount)
        ingested = ts + timedelta(minutes=1)
        if status == "refunded":
            # 처음엔 paid로 들어오고, 며칠 뒤 같은 payment_id가 refunded로 다시 들어온다
            rows.append([payment_id, user_id, _fmt_ts(ts, rng), _messy(plan, rng), amount_text, "paid",
                         ingested.strftime("%Y-%m-%d %H:%M:%S")])
            ingested = ingested + timedelta(days=3)
        rows.append([payment_id, user_id, _fmt_ts(ts, rng), _messy(plan, rng), amount_text,
                     _messy(status, rng), ingested.strftime("%Y-%m-%d %H:%M:%S")])
    cols = ["payment_id", "user_id", "paid_at", "plan", "amount", "status", "ingested_at"]
    return pd.DataFrame(rows, columns=cols)


def make_raw(n_users=2000, seed=42):
    """원본 테이블 3개를 dict로 돌려준다. 키는 raw_users, raw_payments, raw_events."""
    rng = np.random.default_rng(seed)
    users = make_users(n_users, rng)
    events, payments = make_events_and_payments(users, rng)
    return {
        "raw_users": users,
        "raw_payments": _payments_frame(payments, rng),
        "raw_events": _events_frame(events, rng),
    }
