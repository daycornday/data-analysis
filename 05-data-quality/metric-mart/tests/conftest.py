import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metric_mart_sql import pipeline, synth  # noqa: E402


@pytest.fixture
def raw_small():
    return synth.make_raw(n_users=300, seed=7)


@pytest.fixture
def built(raw_small):
    """작은 합성 데이터로 전체 레이어를 만든 연결. 테스트마다 새로 만든다."""
    conn = pipeline.connect()
    pipeline.load_raw(conn, raw_small)
    pipeline.build(conn)
    yield conn
    conn.close()
