import subprocess
import sys

from check_doc import check
from conftest import MIDDLE_DOT, ROOT

SCRIPT = ROOT / "automation" / "check_doc.py"
SHORT = {"min_chars": 200, "max_chars": 12000}


def test_good_post_passes(good_post):
    assert check(good_post, [], **SHORT) == []


def test_middle_dot_fails(good_post):
    errors = check(good_post.replace("결과표", "결과{}표".format(MIDDLE_DOT)), [], **SHORT)
    assert errors == ["가운뎃점 U+00B7 1개"]


def test_banned_word_fails(good_post):
    errors = check(good_post + "\n사내 전용 수치\n", ["사내 전용"], **SHORT)
    assert errors == ["금지어: 사내 전용"]


def test_review_mark_blocks_publish(good_post):
    errors = check(good_post.replace("보통 0.001", "[확인 필요] 0.001"), [], **SHORT)
    assert errors == ["사람 확인 표시 1개 남음"]


def test_missing_front_matter_and_section(good_post):
    body = good_post.split("---\n", 2)[2].replace("## 정리", "## 마무리")
    errors = check(body, [], **SHORT)
    assert "머리말(---) 없음" in errors
    assert "섹션 없음: ## 정리" in errors


def test_reading_list_needs_link(good_post):
    errors = check(good_post.replace("https://experimentguide.com/", "책 참고"), [], **SHORT)
    assert errors == ["더 읽을 것에 링크 없음"]


def test_length_limit(good_post):
    assert check(good_post, [])[0].startswith("본문 길이")


def run_cli(path):
    cmd = [sys.executable, "-X", "utf8", str(SCRIPT), str(path), "--min-chars", "200"]
    return subprocess.run(cmd, capture_output=True).returncode


def test_cli_exit_codes(tmp_path, good_post):
    good = tmp_path / "good.md"
    good.write_text(good_post, encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text(good_post.replace("결과표", "결과{}표".format(MIDDLE_DOT)), encoding="utf-8")
    assert (run_cli(good), run_cli(bad)) == (0, 1)
