"""저장소 전체 검사: 금지 문자, 금지어, 폴더 구조. CI와 로컬에서 같이 쓴다."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED_WORDS = ["미리디", "미리캔버스", "비즈하우스", "캐치테이블", "더에스엠씨", "유효채택", "서브큐", "amint9410", "C:" + "\\" + "Users"]
TEXT_EXT = {".md", ".py", ".sql", ".json", ".yml", ".yaml", ".txt", ".csv"}
SKIP = {".git", "__pycache__", ".pytest_cache"}
PROJECT_FILES = ["README.md"]


def text_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in TEXT_EXT and not SKIP & set(p.parts) and p.name not in ("check_repo.py", "CONVENTIONS.md"):
            yield p


def main():
    errors = []
    for p in text_files():
        text = p.read_text(encoding="utf-8", errors="replace")
        rel = p.relative_to(ROOT)
        if "\u00b7" in text:
            errors.append(f"{rel}: 가운뎃점 {text.count(chr(0xB7))}개")
        for w in BANNED_WORDS:
            if w in text:
                errors.append(f"{rel}: 금지어 {w}")
    for d in sorted(p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith((".", "_")) and p.name != "scripts"):
        for f in PROJECT_FILES:
            if not (d / f).exists():
                errors.append(f"{d.name}: {f} 없음")
        if (d / "run.py").exists() and not (d / "tests").exists():
            errors.append(f"{d.name}: run.py는 있는데 tests 없음")
    for e in errors:
        print("FAIL", e)
    print("repo ok" if not errors else f"{len(errors)}건 실패")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
