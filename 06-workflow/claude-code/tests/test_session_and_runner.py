"""세션 시작 훅과 러너의 결과 판단을 임시 상태 폴더에서 확인한다."""
import datetime as dt
import json

import notify
import run_publish
import session_status

NOW = dt.datetime(2026, 1, 20, 9, 0)


def write_result(folder, **fields):
    base = {"run_started": "2026-01-20T08:30:00", "dry_run": False, "overall": "ok", "actions_needed": []}
    base.update(fields)
    (folder / "last_run.json").write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")


def test_quiet_when_nothing_to_report(state):
    write_result(state)
    assert session_status.build_lines(state, NOW) == []


def test_unseen_notes_shown_once(state):
    notify.send("발행 실패", "결과 파일이 없다", "high")
    first = session_status.build_lines(state, NOW)
    assert len(first) == 1 and first[0].startswith("[!]")
    assert session_status.build_lines(state, NOW) == []


def test_failed_run_shows_human_actions(state):
    write_result(state, overall="failed", actions_needed=["로그인 다시 하기"])
    lines = session_status.build_lines(state, NOW)
    assert lines == ["[!] 마지막 실행 결과: failed", "    사람이 할 일: 로그인 다시 하기"]


def test_dry_run_failure_is_not_alarmed(state):
    write_result(state, overall="failed", dry_run=True)
    assert session_status.build_lines(state, NOW) == []


def test_stale_schedule_warning(state):
    (state / "last_real_run.txt").write_text("2026-01-01T09:00:00", encoding="utf-8")
    assert "19일째" in session_status.build_lines(state, NOW)[0]


def test_runner_flags_missing_result():
    title, _, priority = run_publish.summarize(None, NOW, 1)
    assert (title, priority) == ("발행 실패", "high")


def test_runner_rejects_old_result():
    old = {"run_started": "2026-01-06T09:00:00", "overall": "ok"}
    assert run_publish.summarize(old, NOW, 0)[0] == "발행 실패"


def test_runner_reports_ok_run():
    fresh = {"run_started": "2026-01-20T09:01:00", "overall": "ok", "post": {"topic": "SRM", "status": "published"}}
    assert run_publish.summarize(fresh, NOW, 0) == ("발행 완료", "글: SRM (published)", "default")


def test_runner_blocks_force_push(state):
    cmd = run_publish.build_command(False, state / "last_run.json")
    assert "Bash(git push --force:*)" in cmd[cmd.index("--disallowedTools") + 1]
