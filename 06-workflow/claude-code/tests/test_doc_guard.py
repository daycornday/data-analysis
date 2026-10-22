"""PreToolUse 훅을 실제처럼 stdin JSON으로 실행해 본다."""
import json
import subprocess
import sys

from conftest import MIDDLE_DOT, ROOT
from doc_guard import decide

HOOK = ROOT / "hooks" / "doc_guard.py"


def run_hook(payload_bytes):
    proc = subprocess.run([sys.executable, str(HOOK)], input=payload_bytes, capture_output=True)
    return proc.returncode, proc.stdout.decode("utf-8")


def write_payload(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def test_write_with_middle_dot_is_denied():
    payload = write_payload("docs/글.md", "지표{}대시보드".format(MIDDLE_DOT))
    code, out = run_hook(json.dumps(payload).encode("utf-8"))
    assert code == 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "U+00B7" in decision["permissionDecisionReason"]


def test_clean_write_passes_silently(good_post):
    code, out = run_hook(json.dumps(write_payload("docs/글.md", good_post)).encode("utf-8"))
    assert (code, out) == (0, "")


def test_banned_word_in_edit_is_denied():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "a.txt", "old_string": "x", "new_string": "대외비 수치"}}
    assert decide(payload, ["대외비"])["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_multiedit_checks_every_edit():
    edits = [{"old_string": "a", "new_string": "괜찮음"}, {"old_string": "b", "new_string": "x" + MIDDLE_DOT}]
    payload = {"tool_name": "MultiEdit", "tool_input": {"file_path": "a.md", "edits": edits}}
    assert decide(payload, []) is not None


def test_edit_only_checks_new_text():
    # 기존 문서에 남은 문자를 고치라고 막지 않는다. 새로 쓰는 부분만 본다
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "a.md", "old_string": MIDDLE_DOT, "new_string": ","}}
    assert decide(payload, []) is None


def test_non_doc_file_is_not_checked():
    assert decide(write_payload("calc.py", "x = '{}'".format(MIDDLE_DOT)), []) is None


def test_broken_stdin_does_not_block():
    assert run_hook(b"not json") == (0, "")
