from conftest import MIDDLE_DOT, ROOT
from text_rules import find_violations, load_banned_words


def test_middle_dot_is_caught():
    problems = find_violations("데이터{}분석".format(MIDDLE_DOT * 2), [])
    assert problems == ["가운뎃점 U+00B7 2개"]


def test_lookalike_dots_and_zero_width_space_are_caught():
    text = "a{}b{}c{}d".format(chr(0x30FB), chr(0xFF65), chr(0x200B))
    assert len(find_violations(text, [])) == 3


def test_banned_word_ignores_case():
    assert find_violations("This is INTERNAL ONLY.", ["internal only"]) == ["금지어: internal only"]


def test_clean_text_passes(good_post):
    assert find_violations(good_post, load_banned_words()) == []


def test_word_file_skips_comments_and_blanks(tmp_path):
    words = tmp_path / "words.txt"
    words.write_text("# 주석\n\n  가나다  \nfoo\n", encoding="utf-8")
    assert load_banned_words(words) == ["가나다", "foo"]


def test_env_var_overrides_default_word_file(tmp_path, monkeypatch):
    words = tmp_path / "private_words.txt"
    words.write_text("비공개단어\n", encoding="utf-8")
    monkeypatch.setenv("BANNED_WORDS_FILE", str(words))
    assert load_banned_words() == ["비공개단어"]


def test_this_folder_has_no_banned_chars():
    # 규칙을 만든 폴더가 규칙을 어기지 않는지 스스로 확인한다
    suffixes = {".md", ".py", ".json", ".txt"}
    dirty = [p.name for p in ROOT.rglob("*") if p.suffix in suffixes and find_violations(p.read_text(encoding="utf-8"), [])]
    assert dirty == []
