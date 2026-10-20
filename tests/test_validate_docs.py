import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "validate_docs", Path(__file__).resolve().parents[1] / "scripts" / "validate_docs.py"
)
validate_docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_docs)

GOOD_META = "---\ntitle: t\ncategory: c\nquestion: q\nrelated: []\nstatus: active\nupdated: 2026-10-20\n---\n"
SECTIONS = "## 언제 쓰나\n## 판단 기준\n## 핵심 패턴\n## 안티패턴\n"


def write(tmp_path, body, name="doc.md"):
    d = tmp_path / "methods"
    d.mkdir(exist_ok=True)
    p = d / name
    p.write_text(body, encoding="utf-8")
    return p


def test_good_method_doc_passes(tmp_path):
    assert validate_docs.check(write(tmp_path, GOOD_META + SECTIONS)) == []


def test_missing_front_matter(tmp_path):
    assert validate_docs.check(write(tmp_path, SECTIONS)) == ["머리말(---) 없음"]


def test_section_order_is_enforced(tmp_path):
    swapped = "## 판단 기준\n## 언제 쓰나\n## 핵심 패턴\n## 안티패턴\n"
    errors = validate_docs.check(write(tmp_path, GOOD_META + swapped))
    assert any("섹션 순서" in e for e in errors)


def test_broken_link_is_caught(tmp_path):
    errors = validate_docs.check(write(tmp_path, GOOD_META + SECTIONS + "[x](nope.md)\n"))
    assert any("깨진 링크" in e for e in errors)


def test_bad_status(tmp_path):
    errors = validate_docs.check(write(tmp_path, GOOD_META.replace("active", "done") + SECTIONS))
    assert any("status" in e for e in errors)
