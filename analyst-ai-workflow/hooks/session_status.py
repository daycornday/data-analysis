"""SessionStart 훅. 자동 작업 상태를 세션 시작 때 한 번 보여 준다.

보여 주는 것 (문제가 없으면 아무것도 출력하지 않는다)
1. 아직 안 본 알림 (state/notifications.jsonl). 보여 준 뒤 읽음 처리
2. 마지막 실행 결과(state/last_run.json)가 ok가 아니면 경고와 사람이 할 일
3. 실제 실행(시험 실행 제외)이 MAX_DAYS일 넘게 없으면 경고. 스케줄러가 멈춘 것을 잡는다

상태 폴더: 환경변수 WORKFLOW_STATE_DIR, 없으면 ../automation/state
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

DEFAULT_STATE = Path(__file__).resolve().parents[1] / "automation" / "state"
MAX_DAYS = int(os.environ.get("WORKFLOW_MAX_DAYS", "15"))


def state_dir():
    return Path(os.environ.get("WORKFLOW_STATE_DIR") or DEFAULT_STATE)


def read_jsonl(path):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def take_unseen_notes(log_path):
    records = read_jsonl(log_path)
    unseen = [r for r in records if not r.get("seen")]
    if unseen:
        for r in records:
            r["seen"] = True
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
        log_path.write_text(text, encoding="utf-8")
    return unseen


def note_lines(notes):
    lines = []
    for n in notes:
        mark = "[!] " if n.get("priority") == "high" else ""
        lines.append("{}{} {}: {}".format(mark, n.get("at", "")[:16], n.get("title", ""), n.get("message", "")))
    return lines


def result_lines(result_path):
    if not result_path.exists():
        return []
    r = json.loads(result_path.read_text(encoding="utf-8"))
    if r.get("dry_run") or r.get("overall") == "ok":
        return []
    lines = ["[!] 마지막 실행 결과: {}".format(r.get("overall", "unknown"))]
    lines += ["    사람이 할 일: {}".format(a) for a in r.get("actions_needed", [])]
    return lines


def stale_lines(last_real_path, now):
    if not last_real_path.exists():
        return []
    last = dt.datetime.fromisoformat(last_real_path.read_text(encoding="utf-8").strip())
    days = (now - last).days
    if days <= MAX_DAYS:
        return []
    return ["[!] 실제 실행이 {}일째 없다. 스케줄러 등록 상태를 확인한다".format(days)]


def build_lines(folder, now):
    lines = note_lines(take_unseen_notes(folder / "notifications.jsonl"))
    lines += result_lines(folder / "last_run.json")
    lines += stale_lines(folder / "last_real_run.txt", now)
    return lines


def main():
    try:
        lines = build_lines(state_dir(), dt.datetime.now())
    except (OSError, ValueError) as e:
        lines = ["[!] 상태 파일을 읽지 못했다: {}".format(e)]
    if lines:
        print(json.dumps({"systemMessage": "자동 작업 상태\n" + "\n".join(lines)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
