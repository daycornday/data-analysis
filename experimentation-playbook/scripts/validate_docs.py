"""docs/ 아래 모든 md 문서의 머리말과 구조를 검사한다. CI에서 실행된다.

- 머리말 필수 필드: title, category, question, related, status, updated
- status는 draft | active | deprecated
- docs/methods/ 문서(템플릿 제외)는 네 섹션을 이 순서로 가져야 한다
  언제 쓰나 → 판단 기준 → 핵심 패턴 → 안티패턴
- 문서 안의 상대 링크가 실제 파일을 가리켜야 한다
"""
import re
import sys
from pathlib import Path

import yaml

DOCS = Path(__file__).resolve().parents[1] / "docs"
REQUIRED = {"title", "category", "question", "related", "status", "updated"}
STATUSES = {"draft", "active", "deprecated"}
METHOD_SECTIONS = ["## 언제 쓰나", "## 판단 기준", "## 핵심 패턴", "## 안티패턴"]
LINK = re.compile(r"\]\(([^)#\s]+\.md)(#[^)]*)?\)")


def front_matter(text):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    return yaml.safe_load(text[4:end]) if end != -1 else None


def check(path):
    errors = []
    text = path.read_text(encoding="utf-8")
    meta = front_matter(text)
    if meta is None:
        return ["머리말(---) 없음"]
    missing = REQUIRED - set(meta)
    if missing:
        errors.append(f"머리말 필드 누락: {sorted(missing)}")
    if meta.get("status") not in STATUSES:
        errors.append(f"status 값이 잘못됨: {meta.get('status')}")
    if path.parent.name == "methods" and not path.name.startswith("_"):
        positions = [text.find(s) for s in METHOD_SECTIONS]
        if -1 in positions or positions != sorted(positions):
            errors.append("방법론 문서 섹션 순서가 '언제 쓰나 → 판단 기준 → 핵심 패턴 → 안티패턴'이 아님")
    for target, _ in LINK.findall(text):
        if target.startswith("http"):
            continue
        if not (path.parent / target).resolve().exists():
            errors.append(f"깨진 링크: {target}")
    return errors


def main():
    failed = False
    for path in sorted(DOCS.rglob("*.md")):
        errors = check(path)
        for e in errors:
            print(f"{path.relative_to(DOCS)}: {e}")
        failed |= bool(errors)
    if failed:
        sys.exit(1)
    print("docs ok")


if __name__ == "__main__":
    main()
