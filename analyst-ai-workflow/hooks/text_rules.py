"""문서 텍스트 규칙. 쓰기 훅(doc_guard.py)과 발행 전 검사(check_doc.py)가 같이 쓴다.

표준 라이브러리만 쓴다. 금지 문자는 코드 안에서도 chr() 코드로만 적는다.
(문자를 그대로 적으면 이 파일 자체가 검사에 걸린다)
"""
import os
from pathlib import Path

BANNED_CHARS = {
    chr(0x00B7): "가운뎃점 U+00B7",
    chr(0x30FB): "가타카나 가운뎃점 U+30FB",
    chr(0xFF65): "반각 가운뎃점 U+FF65",
    chr(0x200B): "폭 없는 공백 U+200B",
}

DEFAULT_WORDS_FILE = Path(__file__).resolve().with_name("banned_words.txt")


def load_banned_words(path=None):
    """금지어 목록을 읽는다. 순서: 인자 > 환경변수 BANNED_WORDS_FILE > 기본 파일."""
    path = Path(path or os.environ.get("BANNED_WORDS_FILE") or DEFAULT_WORDS_FILE)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def find_banned_chars(text):
    found = []
    for ch, label in BANNED_CHARS.items():
        count = text.count(ch)
        if count:
            found.append("{} {}개".format(label, count))
    return found


def find_banned_words(text, banned_words):
    lower = text.lower()
    return ["금지어: {}".format(w) for w in banned_words if w.lower() in lower]


def find_violations(text, banned_words):
    return find_banned_chars(text) + find_banned_words(text, banned_words)
