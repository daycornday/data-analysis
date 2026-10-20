import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for sub in ("hooks", "automation"):
    sys.path.insert(0, str(ROOT / sub))

MIDDLE_DOT = chr(0xB7)


@pytest.fixture
def good_post():
    return (ROOT / "tests" / "fixtures" / "good_post.md").read_text(encoding="utf-8")


@pytest.fixture
def state(tmp_path, monkeypatch):
    """상태 폴더를 임시 폴더로 돌린다. 실제 알림 기록을 건드리지 않는다."""
    monkeypatch.setenv("WORKFLOW_STATE_DIR", str(tmp_path))
    return tmp_path
