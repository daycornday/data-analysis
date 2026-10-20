"""레이어가 순서대로 만들어지고, 손으로 계산한 정답을 되찾는지 확인한다."""
import pandas as pd
import pytest

from metric_mart_sql import pipeline


def one(conn, sql):
    return conn.execute(sql).fetchone()[0]


def test_sql_files_have_grain_comment():
    for path in pipeline.sql_files():
        first = path.read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("-- " + path.stem), path
        assert pipeline.grain_of(path), path


def test_naming_prefix_matches_layer():
    prefix = {"01_staging": ("stg_",), "02_marts": ("fct_", "dim_"), "03_metrics": ("metric_",)}
    for path in pipeline.sql_files():
        assert path.stem.startswith(prefix[path.parent.name]), path


def test_staging_removes_duplicates_and_anonymous(built, raw_small):
    raw_events = raw_small["raw_events"]
    expected = raw_events[raw_events["user_id"].notna()]["event_id"].nunique()
    assert len(raw_events) > expected
    assert one(built, "SELECT count(*) FROM stg_events") == expected
    assert one(built, "SELECT count(*) FROM stg_users") == raw_small["raw_users"]["user_id"].nunique()


def test_staging_normalizes_types(built):
    assert one(built, "SELECT count(*) FROM stg_payments WHERE typeof(amount) != 'integer'") == 0
    assert one(built, "SELECT count(*) FROM stg_events WHERE event_at LIKE '%T%'") == 0
    statuses = {r[0] for r in built.execute("SELECT DISTINCT status FROM stg_payments")}
    assert statuses <= {"paid", "failed", "refunded"}


def test_dim_date_has_no_gaps(built):
    n_rows = one(built, "SELECT count(*) FROM dim_date")
    span = one(built, "SELECT julianday(max(date_day)) - julianday(min(date_day)) + 1 FROM dim_date")
    assert n_rows == span


def _tiny_raw():
    """손으로 정답을 계산할 수 있는 원본 3개."""
    users = pd.DataFrame({
        "user_id": ["1", "2", "3"],
        "signup_at": ["2026-01-01 09:00:00", "2026-01-01T10:00:00Z", "2026-01-02 11:00:00"],
        "channel": ["organic", " PAID_SEARCH", "Referral "],
        "country": ["kr", "kr", "jp"],
        "ingested_at": ["2026-01-01 09:00:01", "2026-01-01 10:00:01", "2026-01-02 11:00:01"],
    })
    events = pd.DataFrame({
        "event_id": ["e1", "e1", "e2", "e3", "e4", "e5", "a1"],
        "user_id": ["1", "1", "1", "2", "3", "3", None],
        "event_name": ["session_start"] * 6 + ["view_item"],
        "event_at": ["2026-01-01 09:00:00", "2026-01-01 09:00:00", "2026-01-09 08:00:00",
                     "2026-01-01 10:00:00", "2026-01-02 11:00:00", "2026-01-31 12:00:00",
                     "2026-01-05 12:00:00"],
        "ingested_at": ["2026-01-01 09:00:05", "2026-01-01 09:03:00", "2026-01-09 08:00:05",
                        "2026-01-01 10:00:05", "2026-01-02 11:00:05", "2026-01-31 12:00:05",
                        "2026-01-05 12:00:05"],
    })
    payments = pd.DataFrame({
        "payment_id": ["p1", "p2", "p3", "p3", "p4"],
        "user_id": ["1", "2", "3", "3", "1"],
        "paid_at": ["2026-01-03 10:00:00", "2026-01-20 10:00:00", "2026-01-05 10:00:00",
                    "2026-01-05 10:00:00", "2026-01-02 10:00:00"],
        "plan": ["monthly", "annual", "monthly", "monthly", "monthly"],
        "amount": ["9900", "99,000", "9,900", "9,900", "9900"],
        "status": ["paid", "PAID", "paid", "refunded", "failed"],
        "ingested_at": ["2026-01-03 10:01:00", "2026-01-20 10:01:00", "2026-01-05 10:01:00",
                        "2026-01-08 10:01:00", "2026-01-02 10:01:00"],
    })
    return {"raw_users": users, "raw_events": events, "raw_payments": payments}


@pytest.fixture
def tiny():
    conn = pipeline.connect()
    pipeline.load_raw(conn, _tiny_raw())
    pipeline.build(conn)
    yield conn
    conn.close()


def test_known_answer_arppu(tiny):
    # 유저1 9,900 + 유저2 99,000 = 108,900, 결제 유저 2명. 유저3은 환불, 유저1의 p4는 실패
    row = tiny.execute("SELECT revenue, paying_users, arppu FROM metric_arppu").fetchall()
    assert row == [(108900, 2, 54450.0)]


def test_known_answer_conversion(tiny):
    # 3명 모두 관측 창 안. 14일 안 첫 결제는 유저1(3일차)뿐. 유저2는 19일차, 유저3은 환불
    row = tiny.execute(
        "SELECT signups, converted_14d, conversion_rate_14d FROM metric_payment_conversion").fetchall()
    assert row == [(3, 1, 0.3333)]


def test_known_answer_dau_and_retention(tiny):
    assert one(tiny, "SELECT dau FROM metric_daily_active WHERE date_day = '2026-01-01'") == 2
    assert one(tiny, "SELECT sum(dau) FROM metric_daily_active") == 5
    cells = tiny.execute(
        "SELECT signup_week, week_n, cohort_size, active_users FROM metric_retention_cohort").fetchall()
    # 1/1(목), 1/2(금) 가입은 12/29 주. 1주차(7~13일차)에 돌아온 사람은 유저1(8일차)
    assert cells[:2] == [("2025-12-29", 0, 3, 3), ("2025-12-29", 1, 3, 1)]
    # 유저3은 29일차(4주차)에 돌아왔지만, 4주차 창(1/2 가입자 기준 2/5까지)이 데이터 끝(1/31)을
    # 넘으므로 아직 관측이 끝나지 않은 칸이다. 표에 넣지 않는다
    assert all(week_n <= 3 for _, week_n, _, _ in cells)
