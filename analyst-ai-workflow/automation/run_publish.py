"""격주 발행 러너. 스케줄러(cron, 윈도우 작업 스케줄러)가 실행한다.

1. Claude Code를 헤드리스(claude -p)로 실행해 publish-knowledge 스킬을 돌린다
2. 스킬이 남긴 state/last_run.json을 읽어 notifications.jsonl에 결과를 남긴다
3. 결과 파일이 없거나 이번 실행 것이 아니면 실패로 기록한다

사용: python run_publish.py              (발행 회차)
     python run_publish.py dry-run      (파일만 만들고 공개하지 않음)

환경변수
- CLAUDE_BIN: claude 실행 파일 (기본 claude, PATH에서 찾는다)
- WORKFLOW_PROJECT_DIR: Claude Code를 실행할 폴더 (기본 저장소 루트)
- WORKFLOW_STATE_DIR: 결과와 알림을 둘 폴더 (기본 automation/state)
"""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from notify import send, state_dir  # noqa: E402

TIMEOUT_MIN = 120
ALLOWED_TOOLS = "Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Bash,Skill"
# 허용 목록만으로는 Bash 안의 위험한 명령을 못 막는다. 거부 목록을 따로 둔다
DENIED_TOOLS = "Bash(git push --force:*),Bash(git push -f:*),Bash(rm -rf:*)"


def build_command(dry, result_path):
    args = "dry-run" if dry else "publish"
    prompt = "publish-knowledge 스킬로 이번 회차를 실행해. 인자: {}. 결과 파일: {}".format(args, result_path)
    claude = os.environ.get("CLAUDE_BIN", "claude")
    return [claude, "-p", prompt, "--allowedTools", ALLOWED_TOOLS, "--disallowedTools", DENIED_TOOLS]


def run_headless(cmd, log_path, cwd):
    env = dict(os.environ, WORKFLOW_STATE_DIR=str(state_dir()))
    with open(log_path, "w", encoding="utf-8") as f:
        proc = subprocess.run(cmd, cwd=str(cwd), env=env, stdout=f, stderr=subprocess.STDOUT,
                              timeout=TIMEOUT_MIN * 60, encoding="utf-8", errors="replace")
    return proc.returncode


def load_result(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def summarize(result, started, code):
    """(제목, 본문, 우선순위). 판단만 하고 기록은 하지 않는다."""
    if result is None:
        return "발행 실패", "결과 파일이 없다. 종료 코드 {}".format(code), "high"
    run_started = dt.datetime.fromisoformat(result.get("run_started", "1970-01-01T00:00:00"))
    # 지난 실행의 결과 파일을 이번 결과로 착각하지 않도록 시각을 비교한다
    if run_started < started - dt.timedelta(minutes=5):
        return "발행 실패", "이번 실행의 결과가 기록되지 않았다. 종료 코드 {}".format(code), "high"
    post = result.get("post", {})
    lines = ["글: {} ({})".format(post.get("topic", "-"), post.get("status", "-"))]
    if result.get("actions_needed"):
        lines.append("사람이 할 일: " + " / ".join(result["actions_needed"]))
    if result.get("dry_run"):
        return "[시험] 실행 완료 (공개 안 함)", "\n".join(lines), "default"
    overall = result.get("overall", "failed")
    titles = {"ok": "발행 완료", "partial": "발행 일부 실패", "failed": "발행 실패"}
    return titles.get(overall, "발행 결과 확인 필요"), "\n".join(lines), "default" if overall == "ok" else "high"


def main(argv):
    dry = "dry-run" in argv
    folder = state_dir()
    (folder / "logs").mkdir(exist_ok=True)
    started = dt.datetime.now()
    log_path = folder / "logs" / "{:%Y%m%d_%H%M}{}.log".format(started, "_dry" if dry else "")
    result_path = folder / "last_run.json"
    project_dir = Path(os.environ.get("WORKFLOW_PROJECT_DIR") or HERE.parents[1])
    try:
        code = run_headless(build_command(dry, result_path), log_path, project_dir)
    except subprocess.TimeoutExpired:
        send("발행 실패", "{}분 안에 끝나지 않아 중단했다".format(TIMEOUT_MIN), "high")
        return 1
    if not dry:
        (folder / "last_real_run.txt").write_text(started.isoformat(timespec="seconds"), encoding="utf-8")
    send(*summarize(load_result(result_path), started, code))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
