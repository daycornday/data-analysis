"""문서의 예시 계산과 statsmodels multipletests 결과를 둘 다 맞추는지 확인한다."""
import numpy as np
import pytest
from statsmodels.stats.multitest import multipletests

from playbook import (
    benjamini_hochberg,
    bonferroni,
    familywise_error,
    holm,
    sample_size_per_group,
)

DOC_P = [0.004, 0.011, 0.019, 0.030, 0.041]
METHODS = [(bonferroni, "bonferroni"), (holm, "holm"), (benjamini_hochberg, "fdr_bh")]


def test_doc_example_reject_counts():
    # 문서 판단 기준 3절: 같은 p값 다섯 개로 본페로니 1개, 홀름 2개, BH 5개
    assert sum(bonferroni(DOC_P)[0]) == 1
    assert sum(holm(DOC_P)[0]) == 2
    assert sum(benjamini_hochberg(DOC_P)[0]) == 5


@pytest.mark.parametrize("func,name", METHODS)
def test_matches_statsmodels_on_doc_example(func, name):
    reject, adjusted = func(DOC_P)
    sm_reject, sm_adjusted, _, _ = multipletests(DOC_P, alpha=0.05, method=name)
    assert reject == list(sm_reject)
    assert adjusted == pytest.approx(list(sm_adjusted))


@pytest.mark.parametrize("func,name", METHODS)
def test_matches_statsmodels_on_random_unsorted_input(func, name):
    # 정렬되지 않은 입력, 동점이 섞인 입력에서도 입력 순서대로 같은 답을 내야 한다
    rng = np.random.default_rng(0)
    for _ in range(50):
        p = list(np.round(rng.uniform(0, 0.2, size=rng.integers(1, 15)), 3))
        reject, adjusted = func(p)
        sm_reject, sm_adjusted, _, _ = multipletests(p, alpha=0.05, method=name)
        assert reject == list(sm_reject)
        assert adjusted == pytest.approx(list(sm_adjusted))


def test_holm_never_rejects_fewer_than_bonferroni():
    rng = np.random.default_rng(1)
    for _ in range(200):
        p = list(rng.uniform(0, 0.1, size=8))
        assert sum(holm(p)[0]) >= sum(bonferroni(p)[0])


def test_familywise_table_and_simulation():
    # 문서 판단 기준 1절 표: 3번 14.3%, 20번 64.2%
    assert familywise_error(0.05, 3) == pytest.approx(0.1426, abs=0.0005)
    assert familywise_error(0.05, 20) == pytest.approx(0.6415, abs=0.0005)
    # 효과가 전혀 없는 검정 20개를 10만 번: 보정 없으면 약 64%, 본페로니면 5% 아래
    rng = np.random.default_rng(7)
    p = rng.uniform(size=(100_000, 20))
    assert (p.min(axis=1) < 0.05).mean() == pytest.approx(0.64, abs=0.01)
    assert (p.min(axis=1) < 0.05 / 20).mean() <= 0.05


def test_extra_arm_sample_size():
    # 문서 핵심 패턴: 실험안 2개를 대조군과만 비교하면 alpha 2.5%, 그룹당 약 1만 7,860명
    assert sample_size_per_group(0.10, 0.01) == 14_749
    assert sample_size_per_group(0.10, 0.01, alpha=0.05 / 2) == 17_860


def test_invalid_inputs():
    with pytest.raises(ValueError):
        holm([])
    with pytest.raises(ValueError):
        benjamini_hochberg([0.01, 1.5])
