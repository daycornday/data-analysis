"""자동 실행 결과를 로컬 파일에 한 줄씩 남긴다. 외부로 보내지 않는다.

state/notifications.jsonl에 쌓이고, 세션 시작 훅(hooks/session_status.py)이 다음 세션에서 보여 준다.

사용: python notify.py "제목" "본문" [high|default]
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

DEFAULT_STATE = Path(__file__).resolve().parent / "state"


def state_dir():
    folder = Path(os.environ.get("WORKFLOW_STATE_DIR") or DEFAULT_STATE)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def send(title, message, priority="default"):
    record = {
        "at": dt.datetime.now().isoformat(timespec="seconds"),
        "title": title,
        "message": message,
        "priority": priority,
        "seen": False,
    }
    with open(state_dir() / "notifications.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


if __name__ == "__main__":
    defaults = ["알림 시험", "알림 기록이 남는지 확인한다", "default"]
    given = sys.argv[1:4]
    send(*(given + defaults[len(given):]))
