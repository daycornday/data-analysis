"""PreToolUse 훅. 문서 파일을 쓰기 직전에 금지 문자와 금지어를 검사해 막는다.

- Write는 content, Edit는 new_string, MultiEdit는 edits[].new_string을 본다
- 문서 확장자(.md, .txt)가 아니면 검사하지 않는다
- Edit는 새로 쓰는 부분만 본다. 기존 문서에 남은 문자는 막지 않는다 (일괄 치환을 유도하지 않기 위해)
- 막을 때는 permissionDecision=deny JSON을 출력한다. Claude가 이유를 읽고 고쳐서 다시 쓴다
- 입력을 못 읽으면 통과시킨다. 훅 오류로 작업 전체가 멈추지 않게 하는 선택이다
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from text_rules import find_violations, load_banned_words  # noqa: E402

DOC_SUFFIXES = {".md", ".txt"}


def written_text(tool_input):
    parts = [tool_input.get("content"), tool_input.get("new_string")]
    parts += [e.get("new_string") for e in tool_input.get("edits") or [] if isinstance(e, dict)]
    return "\n".join(p for p in parts if isinstance(p, str))


def decide(payload, banned_words):
    """막아야 하면 훅 출력 dict, 통과면 None."""
    tool_input = payload.get("tool_input") or {}
    path = Path(tool_input.get("file_path") or "")
    if path.suffix.lower() not in DOC_SUFFIXES:
        return None
    problems = find_violations(written_text(tool_input), banned_words)
    if not problems:
        return None
    reason = "{}: 쓸 수 없는 내용 ({}). 고친 뒤 다시 쓴다.".format(path.name, ", ".join(problems))
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def read_payload():
    # 윈도우 기본 stdin 인코딩으로 읽으면 한글 경로가 깨진다. 바이트로 읽어 UTF-8로 푼다
    raw = sys.stdin.buffer.read()
    return json.loads(raw.decode("utf-8", "replace"))


def main():
    try:
        payload = read_payload()
    except ValueError:
        return 0
    result = decide(payload, load_banned_words())
    if result:
        # ensure_ascii 기본값: 콘솔 인코딩과 상관없이 깨지지 않는다
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
