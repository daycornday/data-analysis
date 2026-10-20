"""발행 전 문서 검사. 하나라도 실패하면 종료 코드 1이고, 그 글은 공개하지 않는다.

검사 항목
1. 머리말(--- 블록)에 title, category, tags가 있고 태그가 3~10개
2. 필수 섹션: 들어가며, 정리, 더 읽을 것. 더 읽을 것에 링크가 1개 이상
3. 금지 문자와 금지어 (hooks/text_rules.py와 같은 규칙)
4. 사람 확인 표시([확인 필요])가 남아 있지 않음
5. 본문 길이가 기준 범위 안
6. 제목 깊이는 ###까지

사용: python check_doc.py 글.md [--min-chars 1500] [--max-chars 12000]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from text_rules import find_violations, load_banned_words  # noqa: E402

REQUIRED_META = ("title", "category", "tags")
REQUIRED_SECTIONS = ("## 들어가며", "## 정리", "## 더 읽을 것")
REVIEW_MARK = "[확인 필요]"


def split_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return None, text
    pairs = [line.split(":", 1) for line in m.group(1).splitlines() if ":" in line]
    return {k.strip(): v.strip() for k, v in pairs}, m.group(2)


def check_meta(meta):
    if meta is None:
        return ["머리말(---) 없음"]
    errors = ["머리말 {} 없음".format(k) for k in REQUIRED_META if not meta.get(k)]
    tags = [t for t in meta.get("tags", "").split(",") if t.strip()]
    if not 3 <= len(tags) <= 10:
        errors.append("태그 {}개 (3~10개)".format(len(tags)))
    return errors


def check_sections(body):
    errors = ["섹션 없음: {}".format(s) for s in REQUIRED_SECTIONS if s not in body]
    reading = body.split("## 더 읽을 것", 1)
    if len(reading) == 2 and "http" not in reading[1]:
        errors.append("더 읽을 것에 링크 없음")
    if re.search(r"(?m)^#### ", body):
        errors.append("#### 제목은 쓰지 않는다 (###까지)")
    return errors


def check(text, banned_words, min_chars=1500, max_chars=12000):
    meta, body = split_front_matter(text)
    errors = check_meta(meta) + check_sections(body)
    errors += find_violations(text, banned_words)
    if REVIEW_MARK in text:
        errors.append("사람 확인 표시 {}개 남음".format(text.count(REVIEW_MARK)))
    if not min_chars <= len(body) <= max_chars:
        errors.append("본문 길이 {}자 (기준 {}~{})".format(len(body), min_chars, max_chars))
    return errors


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--min-chars", type=int, default=1500)
    parser.add_argument("--max-chars", type=int, default=12000)
    args = parser.parse_args(argv)
    path = Path(args.path)
    errors = check(path.read_text(encoding="utf-8"), load_banned_words(), args.min_chars, args.max_chars)
    for e in errors:
        print("FAIL", e)
    if errors:
        return 1
    print("PASS", path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
