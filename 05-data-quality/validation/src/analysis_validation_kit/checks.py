"""검사 함수. 모두 같은 모양의 결과(dict)를 돌려준다.

level은 그 검사가 통과하면 올려 줄 수 있는 검증 레벨이다.
- V1: 마트 안에서만 본 자기 일관성 (내가 나를 채점)
- V2: 내가 만들지 않은 기준(원천 로그, 외부 기준 수치)과 일부(합계 한 개, 컬럼 일부)를 맞춤
- V3: 외부 기준과 전 기간, 전 컬럼을 셀 단위로 맞춤
"""
import datetime as dt


def _result(table, check, level, passed, detail):
    return {"table": table, "check": check, "level": level, "passed": bool(passed), "detail": detail}


def _scalar(conn, sql):
    return conn.execute(sql).fetchone()[0]


def check_row_count(conn, table, source_sql, level="V2"):
    """행 수 보존: 마트의 행 수가 원천 기준 행 수와 같은가 (조인 fan-out, 누락 탐지)."""
    got = _scalar(conn, "SELECT COUNT(*) FROM " + table)
    want = _scalar(conn, source_sql)
    return _result(table, "행 수 보존", level, got == want,
                   "마트 {:,}행 / 원천 {:,}행".format(got, want))


def check_key_unique(conn, table, keys, level="V1"):
    """키 유일성: 키 조합이 중복된 행이 0개여야 한다."""
    key_list = ", ".join(keys)
    dup = _scalar(conn, "SELECT COUNT(*) FROM (SELECT {k} FROM {t} GROUP BY {k} HAVING COUNT(*) > 1)"
                  .format(k=key_list, t=table))
    return _result(table, "키 유일성", level, dup == 0, "중복 키 {:,}개 ({})".format(dup, key_list))


def check_sum_matches(conn, table, mart_sql, source_sql, label, level="V2"):
    """합계 대조: 마트 합계와 기준 합계가 같은가."""
    got = _scalar(conn, mart_sql) or 0
    want = _scalar(conn, source_sql) or 0
    return _result(table, "합계 대조", level, got == want,
                   "{}: 마트 {:,} / 기준 {:,} (차이 {:+,})".format(label, got, want, got - want))


def check_denominator(conn, table, mart_sql, numerator_sql, definition_sql, level="V2"):
    """분모 정의 확인: 마트 분모가 지표 정의서의 모집단 수와 같고, 분자가 분모를 넘지 않는가."""
    got = _scalar(conn, mart_sql)
    want = _scalar(conn, definition_sql)
    numer = _scalar(conn, numerator_sql)
    passed = got == want and numer <= got
    return _result(table, "분모 정의 확인", level, passed,
                   "마트 분모 {:,} / 정의상 모집단 {:,}, 분자 {:,}".format(got, want, numer))


def check_ratio(conn, table, num_col, den_col, ratio_col, level="V1", tol=1e-9):
    """비율 계산 확인: 저장된 비율이 같은 행의 분자 / 분모(실수 나눗셈)와 같은가. 정수 나눗셈 탐지."""
    num, den, ratio = conn.execute("SELECT {}, {}, {} FROM {}".format(num_col, den_col, ratio_col, table)).fetchone()
    want = num / den if den else float("nan")
    passed = den not in (0, None) and abs(ratio - want) < tol
    return _result(table, "비율 계산 확인", level, passed,
                   "저장값 {} / 분자÷분모 {:.4f}".format(ratio, want))


def check_period(conn, table, date_col, start, end, level="V1"):
    """경계 확인: 날짜가 start~end(양끝 포함)를 빠짐없이, 넘치지 않게 덮는가."""
    expected = (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days + 1
    first, last, days = conn.execute(
        "SELECT MIN({c}), MAX({c}), COUNT(DISTINCT {c}) FROM {t}".format(c=date_col, t=table)).fetchone()
    passed = first == start and last == end and days == expected
    return _result(table, "경계 확인", level, passed,
                   "{}~{}, {}일 / 기대 {}~{}, {}일".format(first, last, days, start, end, expected))


def check_full_reconcile(conn, table, ref_table, key, cols, level="V3"):
    """전수 대조: 외부 기준 테이블과 모든 키, 모든 컬럼을 셀 단위로 맞춘다."""
    mart = {r[0]: r[1:] for r in conn.execute("SELECT {}, {} FROM {}".format(key, ", ".join(cols), table))}
    ref = {r[0]: r[1:] for r in conn.execute("SELECT {}, {} FROM {}".format(key, ", ".join(cols), ref_table))}
    keys = set(mart) | set(ref)
    bad = [k for k in keys if mart.get(k) != ref.get(k)]
    cells = len(keys) * len(cols)
    return _result(table, "전수 대조", level, not bad,
                   "{}키 x {}컬럼 = {}셀 중 불일치 키 {}개{}".format(
                       len(keys), len(cols), cells, len(bad), " ({})".format(sorted(bad)[:3]) if bad else ""))
