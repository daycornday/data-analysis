import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analysis_validation_kit import make_source, build_marts  # noqa: E402


def _mart(version):
    conn = sqlite3.connect(":memory:")
    make_source(conn, seed=20261020, n_users=400)
    build_marts(conn, version)
    return conn


@pytest.fixture(scope="session")
def buggy():
    conn = _mart("buggy")
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def fixed():
    conn = _mart("fixed")
    yield conn
    conn.close()
