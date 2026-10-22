# 실험 플레이북

A/B 테스트를 설계하거나 결과를 볼 때 "몇 명이면 되지?", "p > 0.05면 효과가 없다고 해도 되나?" 같은 질문에서 자주 헷갈렸습니다. 방법은 알아도 판단 기준을 설명하지 못하는 경우가 많아서, 실무에서 쓰면서 헷갈렸던 기준을 한 문서씩 정리하고 있습니다.

문서마다 언제 쓰는지, 무엇을 기준으로 판단하는지, 자주 쓰는 패턴, 그리고 틀리기 쉬운 지점(안티패턴) 순서로 썼습니다. 문서에 나오는 식은 코드로 옮겨서 테스트로 다시 계산해 봤습니다.

## 지금까지 쓴 문서

| 문서 | 답하는 질문 |
|---|---|
| [검정력과 표본 크기](docs/methods/power-and-sample-size.md) | 몇 명, 며칠? p > 0.05면 효과가 없는 건가? |
| [z 검정과 t 검정](docs/methods/z-vs-t.md) | 두 그룹 비교에 z와 t 중 무엇을? 표본이 크면 차이가 있나? |
| [방법 고르기](docs/decision-tree.md) | 무작위 배정이 안 되면 무엇을 쓰나? |
| [실험 설계서](docs/forms/experiment-design.md), [결과 보고서](docs/forms/results-report.md) | 실험 전에 무엇을 고정하고, 결과를 어떻게 보고하나? |

다음에 쓸 문서와 순서는 [로드맵](docs/roadmap.md)에 적어 두었습니다.

## 폴더 구성

```
playbook/
├── docs/
│   ├── index.md              ← 질문으로 찾기 (이 질문이면 이 문서)
│   ├── decision-tree.md      ← 상황별 방법 고르기 (무작위 가능? → 유저 단위? → …)
│   ├── methods/              ← 방법론 문서. 모두 같은 4단 구조
│   │   ├── _template.md      ← 새 문서는 여기서 시작
│   │   ├── power-and-sample-size.md
│   │   └── z-vs-t.md
│   ├── forms/                ← 실험 설계서, 결과 보고서 양식
│   ├── roadmap.md            ← 다음에 쓸 문서와 순서
│   └── assets/               ← 그림 (스크립트로 다시 생성 가능)
├── src/playbook/             ← 문서의 식을 옮긴 함수 (표본 크기, 검정력, MDE, 다중 비교)
├── tests/                    ← 문서 예시값과 statsmodels 결과를 함께 맞추는 테스트
├── scripts/
│   ├── make_power_figures.py ← 그림 생성
│   └── validate_docs.py      ← 머리말, 섹션 순서, 링크 검사 (저장소 CI에서 실행)
```

## 직접 돌려 보기

```bash
pip install -r ../../requirements.txt
python -m pytest tests -q          # 계산 검증
python scripts/validate_docs.py    # 문서 형식 검사
```

```python
# src/ 를 경로에 넣은 상태에서
from playbook import sample_size_per_group, mde_given_n

sample_size_per_group(p0=0.10, mde=0.01)   # 그룹당 14,749명
mde_given_n(p0=0.10, n_per_group=5_000)    # 5천 명으로 잡을 수 있는 최소 차이
```

## 이렇게 정리한 이유

방법 자체보다 어디서 틀리는지를 아는 쪽이 실무에서 더 도움이 됐습니다. 그래서 문서마다 안티패턴을 따로 두었고, 제가 직접 겪었던 실수를 회사 정보 없이 일반적인 상황으로 바꿔 적었습니다.

문서에 적은 예시 숫자(그룹당 약 1만 4,750명 등)는 `tests/`에서 statsmodels 결과와 같이 다시 계산해 봅니다. 나중에 식을 고쳤을 때 문서와 코드가 어긋나면 바로 알 수 있게 하려고 했습니다. 새 문서를 쓸 때 4단 구조나 머리말을 빠뜨리는 실수도 있어서, 형식 검사도 저장소 CI에 붙여 두었습니다.

문서에 나오는 수치는 모두 가상 시나리오입니다. 실제 서비스 데이터는 쓰지 않았습니다.
